import torch
import torch.nn as nn


class ScaledTanh(nn.Module):
    def forward(self, x):
        return 1.7159 * torch.tanh(2 / 3 * x)


class DebtModel(nn.Module):
    def __init__(self, input_size: int, output_size: int, device: str | None = None):
        super(DebtModel, self).__init__()
        self.input_size = input_size
        self.output_size = output_size
        self.seq = nn.Sequential(
            nn.Linear(input_size, 64, device=device),
            nn.ReLU(),
            nn.Linear(64, 64, device=device),
            nn.ReLU(),
            nn.Linear(64, 64, device=device),
            nn.ReLU(),
            nn.Linear(64, output_size, device=device),
        )

    def forward(self, x) -> torch.Tensor:
        return self.seq(x)


def load_or_create_model(
    path: str, input_size: int, output_size: int, device: str | None
) -> DebtModel:
    # if path exists, load the model
    # else create a new model
    model = DebtModel(input_size, output_size, device)
    try:
        model.load_state_dict(torch.load(path))
        print("MODEL LOADED")
    except Exception as _ex:
        print(f"ERROR BY LOADING THE MODEL FROM {path}")
        pass
    return model
