"""Entry point for running evc-batch-decoder as a module."""
# pylint: disable=invalid-name

from .cli import decode_batch

if __name__ == "__main__":
    decode_batch()  # pylint: disable=no-value-for-parameter
