"""weaver network config: ParticleNet (weaver.nn.model.ParticleNet) on pf_points/pf_features/pf_mask.

Adapted from networks/example_ParticleNet.py in jet-universe/particle_transformer
(MIT), without the lorentz_vectors input. Defaults are a CPU-sized "lite"
network; pass `-o conv_params ... -o fc_params ...` or edit for the full
ParticleNet (k=16; (64,64,64), (128,128,128), (256,256,256); fc (256, 0.1)).
"""
import torch
from weaver.nn.model.ParticleNet import ParticleNet


class ParticleNetWrapper(torch.nn.Module):
    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.mod = ParticleNet(**kwargs)

    def forward(self, points, features, mask):
        return self.mod(points, features, mask)


def get_model(data_config, **kwargs):
    conv_params = [(16, (32, 32, 32)), (16, (64, 64, 64))]   # lite; full: see docstring
    fc_params = [(128, 0.1)]
    model = ParticleNetWrapper(
        input_dims=len(data_config.input_dicts['pf_features']),
        num_classes=len(data_config.label_value),
        conv_params=kwargs.get('conv_params', conv_params),
        fc_params=kwargs.get('fc_params', fc_params),
        use_fusion=kwargs.get('use_fusion', False),
        use_fts_bn=kwargs.get('use_fts_bn', True),
        use_counts=kwargs.get('use_counts', True),
        for_inference=kwargs.get('for_inference', False),
    )
    model_info = {
        'input_names': list(data_config.input_names),
        'input_shapes': {k: ((1,) + s[1:]) for k, s in data_config.input_shapes.items()},
        'output_names': ['softmax'],
        'dynamic_axes': {**{k: {0: 'N', 2: 'n_' + k.split('_')[0]} for k in data_config.input_names},
                         **{'softmax': {0: 'N'}}},
    }
    return model, model_info


def get_loss(data_config, **kwargs):
    return torch.nn.CrossEntropyLoss()
