from __future__ import annotations
import json
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import litellm

from bitwig_agent.client import BitwigClient
from bitwig_agent.llm.tools import BITWIG_TOOLS, ToolExecutor
from bitwig_agent.antigravity import AntigravityClient

load_dotenv()

SYSTEM_PROMPT = """You are the Bitwig Studio Musical AI Agent.
You are an expert music producer, arranger, and jazz/classical/pop/electronic harmony specialist connected in real-time to Bitwig Studio 6.0.

You have access to tools that can:
1. Inspect the open Bitwig project (`get_project_context`), tracks (`inspect_track`), and individual clips with piano rolls (`inspect_clip`).
2. Generate sophisticated, smoothly-voiced, humanized chord progressions directly on any track (`create_chord_progression`).
3. Generate matching basslines (`create_bassline`).
4. Design detailed clips note-by-note with custom melodies, riffs, drum patterns, and pitch/timing/velocity control (`write_notes`).
5. Add instrument tracks or native synths (`add_instrument_track`).
6. Control playback and tempo (`control_transport`).
7. Clear or delete clips (`clear_clip`).

Musical Guidelines:
- Think in harmonic flow: recommend progressions with rich voicings (e.g. 7ths, 9ths, 11ths, 13ths, altered dominants, secondary dominants, modal interchange).
- When writing custom notes (`write_notes`), you can specify pitches by name (e.g. 'C4', 'F#3') or MIDI numbers, and positions by 16th-note steps or beats.
- When a user asks for a progression, choose appropriate chords, rhythm pattern ('sustained', 'lofi', 'syncopated', 'quarter_stabs', 'arpeggio'), and voicing style.
- Always check project tracks first if you are unsure which track to write to, or use the track name requested by the user.
- Explain your harmonic reasoning concisely in natural language to the user (e.g. explaining the voice leading or resolution of tension).
"""

class BitwigAgent:
    """
    Autonomous or interactive agent that uses LiteLLM or Antigravity to interpret
    musical intentions and translate them into live actions in Bitwig Studio.
    """
    def __init__(
        self,
        model: str = "gemini/gemini-2.5-flash",
        client: Optional[BitwigClient] = None,
        session_id: Optional[str] = None,
        session_title: Optional[str] = None
    ):
        self.model = model
        self.client = client or BitwigClient()
        self.executor = ToolExecutor(self.client)
        self.session_id = session_id
        self.session_title = session_title
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    def load_history(
        self,
        messages: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> None:
        if session_id:
            self.session_id = session_id
        if title:
            self.session_title = title

        # Ensure system prompt is at the beginning
        if not messages or messages[0].get("role") != "system":
            self.messages = [{"role": "system", "content": SYSTEM_PROMPT}] + list(messages)
        else:
            self.messages = list(messages)

    def reset_history(self) -> None:
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.session_id = None
        self.session_title = None

    def _call_model(self) -> Any:
        """
        Dispatches request to AntigravityClient, KiloCode Gateway, or standard LiteLLM.
        """
        if self.model.startswith("antigravity/"):
            return AntigravityClient.completion(
                model=self.model,
                messages=self.messages,
                tools=BITWIG_TOOLS,
            )

        if self.model.startswith("kilocode/"):
            # KiloCode Gateway is OpenAI compatible
            kilo_model = self.model[len("kilocode/"):]
            kilo_key = os.getenv("KILOCODE_API_KEY")
            return litellm.completion(
                model=f"openai/{kilo_model}",
                api_base="https://api.kilo.ai/api/gateway/v1",
                api_key=kilo_key,
                messages=self.messages,
                tools=BITWIG_TOOLS,
                tool_choice="auto",
            )

        # Standard LiteLLM provider
        return litellm.completion(
            model=self.model,
            messages=self.messages,
            tools=BITWIG_TOOLS,
            tool_choice="auto",
        )

    def chat(self, user_prompt: str) -> str:
        """
        Sends a user prompt, executes any necessary tool calls in Bitwig,
        and returns the final assistant message.
        """
        self.messages.append({"role": "user", "content": user_prompt})

        max_turns = 8
        turn = 0

        while turn < max_turns:
            turn += 1

            response = self._call_model()

            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None)

            # Convert message to dict format for message history
            msg_dict: Dict[str, Any] = {
                "role": "assistant",
                "content": message.content or ""
            }
            if tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": getattr(tc, "id", f"call_{i}"),
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for i, tc in enumerate(tool_calls)
                ]

            self.messages.append(msg_dict)

            if not tool_calls:
                return message.content or ""

            # Execute each tool call
            for tc in tool_calls:
                fn_name = tc.function.name
                tc_id = getattr(tc, "id", "")
                try:
                    args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
                except Exception:
                    args = {}

                result = self.executor.execute(fn_name, args)

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "name": fn_name,
                    "content": json.dumps(result)
                })

        return "Max tool turns exceeded."
