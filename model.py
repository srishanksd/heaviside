import torch
import torch.nn as nn


class GroundwaterLSTM(nn.Module):

    def __init__(
        self,
        input_size,
        hidden_size=128,
        num_layers=2,
        dropout=0.2
    ):
        super().__init__()

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True
        )

        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 1)
        )

    def forward(self, x):

        # x:
        # [batch, sequence_length, input_size]

        output, _ = self.lstm(x)

        # Last timestep
        last_output = output[:, -1, :]

        prediction = self.fc(last_output)

        return prediction.squeeze(1)