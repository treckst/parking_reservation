"""Exercise model client boundaries with mocked OpenAI constructors and calls."""

import socket
from unittest.mock import Mock, patch

from langchain_core.messages import AIMessage
from pydantic import BaseModel
import pytest

from parking.models import create_embeddings, create_llm


def test_embeddings_use_requested_defaults_without_credentials():
    client = Mock()
    client.embed_query.return_value = [0.2, 0.4]
    with patch("parking.models.OpenAIEmbeddings", return_value=client) as constructor:
        embeddings = create_embeddings()
        assert embeddings.embed_query("parking hours") == [0.2, 0.4]
    constructor.assert_called_once_with(check_embedding_ctx_length=False)
    client.embed_query.assert_called_once_with("parking hours")


def test_llm_uses_exact_model_without_credentials():
    reply = AIMessage(content="Parking is open from 06:00 to 22:00.")
    client = Mock()
    client.invoke.return_value = reply
    with patch("parking.models.ChatOpenAI", return_value=client) as constructor:
        llm = create_llm()
        assert llm.invoke("What are the opening hours?") == reply
    constructor.assert_called_once_with(model="gpt-6-luna")
    client.invoke.assert_called_once_with("What are the opening hours?")


def test_structured_output_uses_mocked_provider():
    class EvidenceAssessment(BaseModel):
        supported: bool

    client = Mock()
    client.with_structured_output.return_value.invoke.return_value = EvidenceAssessment(supported=True)
    with patch("parking.models.ChatOpenAI", return_value=client):
        judge = create_llm().with_structured_output(EvidenceAssessment)
        assert judge.invoke("Assess supplied parking evidence").supported
    client.with_structured_output.assert_called_once_with(EvidenceAssessment)


def test_unit_tests_block_accidental_network_calls():
    with socket.socket() as connection:
        with pytest.raises(AssertionError, match="Network access is disabled"):
            connection.connect(("127.0.0.1", 443))
