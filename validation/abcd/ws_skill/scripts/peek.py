import pyarrow.parquet as pq, sys, fsspec
u='tmp/g0.parquet'
f=pq.ParquetFile(u)
print(f.metadata.num_rows, f.metadata.num_row_groups)
print([n for n in f.schema_arrow.names if n.startswith('HLT')])
