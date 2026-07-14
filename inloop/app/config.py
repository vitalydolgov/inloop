"""Ports for reading application configuration, composed a section per concern."""

from typing import Protocol

from inloop.app.model_config import ModelConfig


class Config(Protocol):
    """Application configuration composed of a section per concern."""

    agent: ModelConfig
    subagent: ModelConfig
