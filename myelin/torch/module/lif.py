import torch

from ..functional.lif import (
    LIFState,
    LIFFeedForwardState,
    LIFParameters,
    lif_step,
    lif_feed_forward_step,
    lif_current_encoder,
)

from typing import Tuple, List
import numpy as np


class LIFCell(torch.nn.Module):
    """
    Parameters:
        shape: Shape of the feedforward state.
        p (LIFParameters): Parameters of the LIF neuron model.
        dt (float): Time step to use.

    Examples::

        >>> batch_size = 16
        >>> lif = LIFCell(10, 20)
        >>> input = torch.randn(batch_size, 10)
        >>> s0 = lif.initial_state(batch_size)
        >>> output, s0 = lif(input, s0)
    """

    def __init__(
        self,
        input_size,
        hidden_size,
        p: LIFParameters = LIFParameters(),
        dt: float = 0.001,
    ):
        super(LIFCell, self).__init__()
        self.input_weights = torch.nn.Parameter(
            torch.randn(hidden_size, input_size) / np.sqrt(input_size)
        )
        self.recurrent_weights = torch.nn.Parameter(
            torch.randn(hidden_size, hidden_size) / np.sqrt(hidden_size)
        )
        self.hidden_size = hidden_size
        self.p = p
        self.dt = dt

    def initial_state(self, batch_size, device, dtype=torch.float) -> LIFState:
        return LIFState(
            z=torch.zeros(batch_size, self.hidden_size, device=device, dtype=dtype),
            v=torch.zeros(batch_size, self.hidden_size, device=device, dtype=dtype),
            i=torch.zeros(batch_size, self.hidden_size, device=device, dtype=dtype),
        )

    def forward(
        self, input: torch.Tensor, state: LIFState
    ) -> Tuple[torch.Tensor, LIFState]:
        return lif_step(
            input,
            state,
            self.input_weights,
            self.recurrent_weights,
            p=self.p,
            dt=self.dt,
        )


class LIFLayer(torch.nn.Module):
    def __init__(self, cell, *cell_args):
        super(LIFLayer, self).__init__()
        self.cell = cell(*cell_args)

    def forward(
        self, input: torch.Tensor, state: LIFState
    ) -> Tuple[torch.Tensor, LIFState]:
        inputs = input.unbind(0)
        outputs = []  # torch.jit.annotate(List[torch.Tensor], [])
        for i in range(len(inputs)):
            out, state = self.cell(inputs[i], state)
            outputs += [out]
        return torch.stack(outputs), state


class LIFFeedForwardCell(torch.nn.Module):
    """
    Parameters:
        shape: Shape of the feedforward state.
        p (LIFParameters): Parameters of the LIF neuron model.
        dt (float): Time step to use.

    Examples::

        >>> batch_size = 16
        >>> lif = LIFFeedForwardCell((20, 30))
        >>> input = torch.randn(batch_size, 20, 30)
        >>> s0 = lif.initial_state(batch_size)
        >>> output, s0 = lif(input, s0)
    """

    def __init__(self, shape, p: LIFParameters = LIFParameters(), dt: float = 0.001):
        super(LIFFeedForwardCell, self).__init__()
        self.shape = shape
        self.p = p
        self.dt = dt

    def initial_state(self, batch_size, device, dtype) -> LIFFeedForwardState:
        return LIFFeedForwardState(
            v=torch.zeros(batch_size, *self.shape, device=device, dtype=dtype),
            i=torch.zeros(batch_size, *self.shape, device=device, dtype=dtype),
        )

    def forward(
        self, input: torch.Tensor, state: LIFFeedForwardState
    ) -> Tuple[torch.Tensor, LIFFeedForwardState]:
        return lif_feed_forward_step(input, state, p=self.p, dt=self.dt)


class LIFConstantCurrentEncoder(torch.nn.Module):
    def __init__(
        self,
        seq_length,
        p: LIFParameters = LIFParameters(),
        dt: float = 0.001,
        device="cpu",
    ):
        super(LIFConstantCurrentEncoder, self).__init__()
        self.seq_length = seq_length
        self.p = p
        self.device = device
        self.dt = dt

    def forward(self, x):
        v = torch.zeros(*x.shape, device=self.device)
        z = torch.zeros(*x.shape, device=self.device)
        voltages = torch.zeros(self.seq_length, *x.shape, device=self.device)
        spikes = torch.zeros(self.seq_length, *x.shape, device=self.device)

        for ts in range(self.seq_length):
            z, v = lif_current_encoder(input_current=x, v=v, p=self.p, dt=self.dt)
            voltages[ts, :, :] = v
            spikes[ts, :, :] = z
        return voltages, spikes
