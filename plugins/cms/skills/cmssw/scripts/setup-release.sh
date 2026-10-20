#!/bin/bash
# Create a CMSSW developer area for ANY release, picking SCRAM_ARCH and the
# OS container automatically; optionally carry user code over from another area.
#
# Non-interactive. Results go to stdout as KEY=VALUE lines; diagnostics to stderr.
# Exit codes: 0 ok, 2 bad usage, 3 release/arch not found, 4 target exists, 5 bad --from.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: setup-release.sh <CMSSW_release> [options]

Create a developer area for <CMSSW_release> (e.g. CMSSW_15_0_21, CMSSW_10_6_30,
CMSSW_14_0_13_patch1). SCRAM_ARCH selection: a build for the host OS if one
exists (preferring the production compiler), else the production arch from
/cvmfs/cms.cern.ch/releases.map. If the arch's OS differs from the host, the
matching cmssw-elX container is reported for cmsenv/build/run.

Options:
  --arch ARCH     Use this SCRAM_ARCH instead of auto-selecting
  --prod          Use the release's production SCRAM_ARCH (as in official
                  production), even if that needs a container
  --dir DIR       Parent directory for the area (default: current directory)
  --name NAME     Directory name of the area (default: the release name)
  --from AREA     Copy user packages from an existing area's src/ (no .git, no build products)
  --list          Only list the architectures the release is built for, then exit
  --dry-run       Print what would be done, change nothing
  -h, --help      Show this help

Output (stdout), e.g.:
  RELEASE=CMSSW_10_6_30
  SCRAM_ARCH=slc7_amd64_gcc700
  AREA=/path/CMSSW_10_6_30
  CONTAINER=cmssw-el7            (or "none")
  ENV_CMD=cmssw-el7 -B /uscms_data -- '...cmsenv...'
EOF
}

CVMFS=/cvmfs/cms.cern.ch
REL="" ARCH="" DIR="$PWD" NAME="" FROM="" LIST=0 DRY=0 PROD=0
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --arch) ARCH="${2:?--arch needs a value}"; shift 2 ;;
    --dir) DIR="${2:?--dir needs a value}"; shift 2 ;;
    --name) NAME="${2:?--name needs a value}"; shift 2 ;;
    --from) FROM="${2:?--from needs a value}"; shift 2 ;;
    --list) LIST=1; shift ;;
    --prod) PROD=1; shift ;;
    --dry-run) DRY=1; shift ;;
    -*) echo "error: unknown option $1" >&2; usage >&2; exit 2 ;;
    *) [ -z "$REL" ] && REL="$1" || { echo "error: extra argument $1" >&2; exit 2; }; shift ;;
  esac
done
[ -n "$REL" ] || { usage >&2; exit 2; }
[[ "$REL" == CMSSW_* ]] || REL="CMSSW_$REL"   # accept 15_0_21 as shorthand
NAME="${NAME:-$REL}"

# shellcheck disable=SC1091
source "$CVMFS/cmsset_default.sh" >/dev/null 2>&1 || true

# --- Which archs is the release built for? (patch releases live in cmssw-patch/)
mapfile -t ARCHS < <(ls -d "$CVMFS"/*/cms/cmssw/"$REL" "$CVMFS"/*/cms/cmssw-patch/"$REL" 2>/dev/null \
  | awk -F/ '{print $4}' | sort -uV)
if [ ${#ARCHS[@]} -eq 0 ]; then
  echo "error: $REL not found on $CVMFS for any architecture." >&2
  echo "       Check the name at https://cmssdt.cern.ch/SDT/ReleaseNotes/" >&2
  exit 3
fi

HOST_OS=$("$CVMFS/common/cmsos" 2>/dev/null || echo unknown_amd64)   # e.g. el9_amd64
HOST_CPU=${HOST_OS#*_}

# OS part of an arch -> container wrapper (major version only).
container_for() {
  case "${1%%_*}" in
    slc5) echo cmssw-el5 ;; slc6) echo cmssw-el6 ;; slc7|cc7) echo cmssw-el7 ;;
    el8|cc8|cs8|alma8|rocky8) echo cmssw-el8 ;; el9|cs9) echo cmssw-el9 ;;
    el10) echo cmssw-el10 ;; *) echo "" ;;
  esac
}
os_major() { local o="${1%%_*}"; echo "${o//[!0-9]/}"; }

# Production arch and release state from CMS's release map (also on CVMFS).
MAP="$CVMFS/releases.map"
PROD_ARCH=$(grep -s "label=$REL;" "$MAP" | grep 'prodarch=1' | sed -n 's/^architecture=\([^;]*\);.*/\1/p' | head -1 || true)
STATE=$(grep -s "label=$REL;" "$MAP" | sed -n 's/.*state=\([^;]*\);.*/\1/p' | head -1 || true)
[ "$STATE" = Deprecated ] && echo "warning: $REL is marked Deprecated; prefer a newer patch release in the same cycle (see https://cmssdt.cern.ch/SDT/ReleaseNotes/)" >&2
compiler() { echo "${1##*_}"; }
if [ $LIST -eq 1 ]; then
  for a in "${ARCHS[@]}"; do [ "$a" = "$PROD_ARCH" ] && echo "$a (production)" || echo "$a"; done
  exit 0
fi

if [ $PROD -eq 1 ]; then
  [ -n "$PROD_ARCH" ] || { echo "error: no production arch recorded for $REL in $MAP" >&2; exit 3; }
  ARCH="$PROD_ARCH"
elif [ -n "$ARCH" ]; then
  printf '%s\n' "${ARCHS[@]}" | grep -qx "$ARCH" || {
    echo "error: $REL is not built for $ARCH. Available: ${ARCHS[*]}" >&2; exit 3; }
else
  # 1) a build for the host OS (no container), same compiler as the production arch if possible;
  # 2) otherwise the production arch (in a container); 3) otherwise the newest host-CPU build.
  NATIVE=$(printf '%s\n' "${ARCHS[@]}" | grep "^${HOST_OS}_" || true)
  if [ -n "$NATIVE" ]; then
    ARCH=$(echo "$NATIVE" | grep "_$(compiler "${PROD_ARCH:-x_x_none}")\$" | head -1 || true)
    ARCH=${ARCH:-$(echo "$NATIVE" | sort -V | tail -1)}
  elif [ -n "$PROD_ARCH" ] && printf '%s\n' "${ARCHS[@]}" | grep -qx "$PROD_ARCH"; then
    ARCH="$PROD_ARCH"
  else
    ARCH=$(printf '%s\n' "${ARCHS[@]}" | grep "_${HOST_CPU}_" | sort -V | tail -1 || true)
  fi
  [ -n "$ARCH" ] || { echo "error: no $HOST_CPU build of $REL. Available: ${ARCHS[*]}" >&2; exit 3; }
fi

if [ "$(os_major "$ARCH")" = "$(os_major "$HOST_OS")" ]; then
  CONTAINER=none
else
  CONTAINER=$(container_for "$ARCH")
  [ -n "$CONTAINER" ] || { echo "error: no known container for $ARCH" >&2; exit 3; }
fi

AREA="$(cd "$DIR" 2>/dev/null && pwd || echo "$DIR")/$NAME"
[ -e "$AREA" ] && { echo "error: $AREA already exists (use --name or --dir)" >&2; exit 4; }

# --- Validate --from before touching anything.
FROM_REL=""
if [ -n "$FROM" ]; then
  FROM="$(cd "$FROM" 2>/dev/null && pwd || true)"
  [ -n "$FROM" ] && [ -d "$FROM/src" ] && compgen -G "$FROM/.SCRAM/*/Environment" >/dev/null || {
    echo "error: --from must be an existing CMSSW area (with src/ and .SCRAM/)" >&2; exit 5; }
  FROM_REL=$(sed -n 's#^RELEASETOP=.*/##p' "$FROM"/.SCRAM/*/Environment | head -1)
fi

# Bind the area's filesystem into the container when it is not visible by default.
BIND=""
case "$AREA" in /uscms_data/*|/uscms/home/*/nobackup*) BIND="-B /uscms_data " ;; esac

if [ "$CONTAINER" = none ]; then
  ENV_CMD="cd $AREA/src && export SCRAM_ARCH=$ARCH && cmsenv"
else
  ENV_CMD="$CONTAINER ${BIND}-- 'cd $AREA/src && export SCRAM_ARCH=$ARCH && source $CVMFS/cmsset_default.sh && cmsenv && <your command>'"
fi

if [ $DRY -eq 1 ]; then
  echo "dry-run: would run: cd $(dirname "$AREA") && scram -a $ARCH project -n $NAME CMSSW $REL" >&2
else
  mkdir -p "$(dirname "$AREA")"
  # scram project itself runs on the host for any arch; only cmsenv/build need the container.
  ( cd "$(dirname "$AREA")" && scram -a "$ARCH" project -n "$NAME" CMSSW "$REL" ) 1>&2 \
    || { echo "error: scram project failed" >&2; exit 3; }
fi

if [ -n "$FROM" ]; then
  RELBASE=$(ls -d "$CVMFS/$ARCH/cms/cmssw/$REL" "$CVMFS/$ARCH/cms/cmssw-patch/$REL" 2>/dev/null | head -1 || true)
  for pkgdir in "$FROM"/src/*/*/; do
    [ -d "$pkgdir" ] || continue
    pkg="${pkgdir%/}"; pkg="${pkg#"$FROM"/src/}"
    if [ -d "$RELBASE/src/$pkg" ]; then
      echo "warning: $pkg is an official CMSSW package (modified copy from $FROM_REL)." >&2
      echo "         Prefer: git cms-addpkg $pkg in the new area and re-apply your changes." >&2
    fi
  done
  if [ $DRY -eq 1 ]; then
    echo "dry-run: would copy $FROM/src/ -> $AREA/src/ (excluding .git)" >&2
  else
    tar -C "$FROM/src" --exclude=.git -cf - . | tar -C "$AREA/src" -xf -
    echo "copied user code from $FROM ($FROM_REL); rebuild with: scram b -j 8" >&2
  fi
fi

echo "RELEASE=$REL"
echo "SCRAM_ARCH=$ARCH"
echo "AVAILABLE_ARCHS=${ARCHS[*]}"
echo "PROD_ARCH=${PROD_ARCH:-unknown}"
echo "STATE=${STATE:-unknown}"
echo "AREA=$AREA"
echo "CONTAINER=$CONTAINER"
[ -n "$FROM_REL" ] && echo "FROM_RELEASE=$FROM_REL"
echo "ENV_CMD=$ENV_CMD"
