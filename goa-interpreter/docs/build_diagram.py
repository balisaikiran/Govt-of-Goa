"""Convert the architecture diagram from simplified MCP format to a proper
Excalidraw scene file that excalidraw.com renders correctly.

The MCP create_view format allows `"label": {"text": "..."}` directly on
shapes. Excalidraw's scene format requires labels to be separate text
elements with `containerId` pointing to the shape, and the shape needs a
`boundElements` array referencing the text element.

Run:  python docs/build_diagram.py
Outputs: docs/architecture.excalidraw  (open in excalidraw.com)
"""

from __future__ import annotations

import json
import random
from pathlib import Path

random.seed(42)

# Simplified diagram elements (same coords as the inline MCP diagram)
SIMPLE: list[dict] = [
    # ---- Title row ----
    {"type": "text", "id": "title", "x": 340, "y": 10, "text": "Goa Interpreter", "fontSize": 36},
    {"type": "text", "id": "sub", "x": 260, "y": 58,
     "text": "Real-time multilingual voice translation, in the master's voice",
     "fontSize": 18, "strokeColor": "#757575"},
    {"type": "text", "id": "stack", "x": 300, "y": 86,
     "text": "WebRTC -> Pipecat -> Deepgram -> GPT-4o-mini -> ElevenLabs",
     "fontSize": 15, "strokeColor": "#8b5cf6"},

    # ---- User-facing zone ----
    {"type": "rectangle", "id": "zoneUser", "x": 10, "y": 120, "width": 1480, "height": 230,
     "backgroundColor": "#dbe4ff", "strokeColor": "#4a9eed", "strokeWidth": 1,
     "opacity": 30, "roundness": 3},
    {"type": "text", "id": "zoneUserL", "x": 24, "y": 128,
     "text": "User-facing layer  (browsers + REST control plane)", "fontSize": 18,
     "strokeColor": "#2563eb"},

    {"type": "rectangle", "id": "master", "x": 40, "y": 170, "width": 200, "height": 140,
     "backgroundColor": "#a5d8ff", "strokeColor": "#2563eb", "strokeWidth": 2, "roundness": 3,
     "label": "Master browser\nclients/master.html\n(LiveKit JS publisher)"},

    {"type": "rectangle", "id": "masterRoom", "x": 300, "y": 190, "width": 230, "height": 100,
     "backgroundColor": "#a5d8ff", "strokeColor": "#2563eb", "strokeWidth": 2, "roundness": 3,
     "label": "LiveKit room\nsession-{id}-master\n(publish-only token)"},

    {"type": "arrow", "id": "a_m2lk", "x": 240, "y": 240, "points": [[0, 0], [60, 0]],
     "strokeColor": "#1e1e1e", "strokeWidth": 2, "label": "mic", "labelFontSize": 14,
     "startBinding": "master", "endBinding": "masterRoom"},

    {"type": "rectangle", "id": "fastapi", "x": 580, "y": 170, "width": 380, "height": 160,
     "backgroundColor": "#fff3bf", "strokeColor": "#f59e0b", "strokeWidth": 2, "roundness": 3},
    {"type": "text", "id": "fapiTitle", "x": 598, "y": 180,
     "text": "FastAPI control plane  (app/server.py)", "fontSize": 17, "strokeColor": "#92400e"},
    {"type": "text", "id": "fapi1", "x": 598, "y": 210,
     "text": "POST /voice/clone -> ElevenLabs IVC", "fontSize": 15},
    {"type": "text", "id": "fapi2", "x": 598, "y": 234,
     "text": "POST /session/start -> mints JWTs, spawns pipeline", "fontSize": 15},
    {"type": "text", "id": "fapi3", "x": 598, "y": 258,
     "text": "POST /session/{id}/stop", "fontSize": 15},
    {"type": "text", "id": "fapi4", "x": 598, "y": 282,
     "text": "GET / | /clients/{master,listener}.html", "fontSize": 15},
    {"type": "text", "id": "fapi5", "x": 598, "y": 306,
     "text": "app/sessions.py: in-mem registry  |  app/livekit_tokens.py: JWT",
     "fontSize": 13, "strokeColor": "#757575"},

    {"type": "arrow", "id": "a_m2api", "x": 140, "y": 170, "points": [[0, 0], [440, 0]],
     "strokeColor": "#f59e0b", "strokeWidth": 2, "strokeStyle": "dashed",
     "label": "REST: clone, start", "labelFontSize": 13},

    # ---- Pipeline zone ----
    {"type": "rectangle", "id": "zonePipe", "x": 10, "y": 380, "width": 1480, "height": 720,
     "backgroundColor": "#e5dbff", "strokeColor": "#8b5cf6", "strokeWidth": 1,
     "opacity": 35, "roundness": 3},
    {"type": "text", "id": "zonePipeL", "x": 24, "y": 390,
     "text": "Pipecat agent process  (app/pipeline.py)  --  app/runner.py spawns one PipelineTask per session",
     "fontSize": 17, "strokeColor": "#6d28d9"},

    {"type": "text", "id": "stage12L", "x": 24, "y": 468, "text": "Stages 1+2",
     "fontSize": 14, "strokeColor": "#6d28d9"},
    {"type": "text", "id": "stage12L2", "x": 24, "y": 486, "text": "capture & ASR",
     "fontSize": 12, "strokeColor": "#757575"},

    {"type": "rectangle", "id": "lkin", "x": 300, "y": 450, "width": 230, "height": 90,
     "backgroundColor": "#a5d8ff", "strokeColor": "#2563eb", "strokeWidth": 2, "roundness": 3,
     "label": "LiveKit input transport\nsubscribes master audio\n16 kHz mono"},
    {"type": "arrow", "id": "a_lkin_vad", "x": 530, "y": 495, "points": [[0, 0], [30, 0]],
     "strokeColor": "#1e1e1e", "strokeWidth": 2,
     "startBinding": "lkin", "endBinding": "vad"},
    {"type": "rectangle", "id": "vad", "x": 560, "y": 450, "width": 200, "height": 90,
     "backgroundColor": "#d0bfff", "strokeColor": "#6d28d9", "strokeWidth": 2, "roundness": 3,
     "label": "Silero VADProcessor\nSileroVADAnalyzer\n200 ms frames"},
    {"type": "arrow", "id": "a_vad_stt", "x": 760, "y": 495, "points": [[0, 0], [30, 0]],
     "strokeColor": "#1e1e1e", "strokeWidth": 2,
     "startBinding": "vad", "endBinding": "stt"},
    {"type": "rectangle", "id": "stt", "x": 790, "y": 450, "width": 240, "height": 90,
     "backgroundColor": "#a5d8ff", "strokeColor": "#2563eb", "strokeWidth": 2, "roundness": 3,
     "label": "Deepgram STT\nmodel=nova-3-general\ninterim_results=True"},
    {"type": "arrow", "id": "a_stt_log", "x": 1030, "y": 495, "points": [[0, 0], [30, 0]],
     "strokeColor": "#1e1e1e", "strokeWidth": 2,
     "startBinding": "stt", "endBinding": "logger"},
    {"type": "rectangle", "id": "logger", "x": 1060, "y": 450, "width": 200, "height": 90,
     "backgroundColor": "#fff3bf", "strokeColor": "#92400e", "strokeWidth": 2, "roundness": 3,
     "label": "Transcription\nLogger\n(debug, pass-through)"},

    {"type": "text", "id": "frameLab1", "x": 540, "y": 546,
     "text": "InterimTranscriptionFrame  +  TranscriptionFrame",
     "fontSize": 12, "strokeColor": "#757575"},

    {"type": "text", "id": "stage3L", "x": 24, "y": 624, "text": "Stage 3",
     "fontSize": 14, "strokeColor": "#6d28d9"},
    {"type": "text", "id": "stage3L2", "x": 24, "y": 642, "text": "orchestrator",
     "fontSize": 12, "strokeColor": "#757575"},

    {"type": "rectangle", "id": "orch", "x": 380, "y": 600, "width": 740, "height": 110,
     "backgroundColor": "#d0bfff", "strokeColor": "#6d28d9", "strokeWidth": 2, "roundness": 3},
    {"type": "text", "id": "orchT", "x": 540, "y": 612,
     "text": "StablePhraseBuffer   (app/orchestrator.py)",
     "fontSize": 18, "strokeColor": "#4c1d95"},
    {"type": "text", "id": "orchT2", "x": 410, "y": 640,
     "text": "DROPS InterimTranscriptionFrame  (no churn downstream)", "fontSize": 14},
    {"type": "text", "id": "orchT3", "x": 410, "y": 662,
     "text": "COALESCES is_final fragments into one stable phrase", "fontSize": 14},
    {"type": "text", "id": "orchT4", "x": 410, "y": 684,
     "text": "FLUSH on:  speech_final  |  '.?!' punctuation  |  4 s timeout", "fontSize": 14},

    {"type": "arrow", "id": "a_log_orch", "x": 1160, "y": 540,
     "points": [[0, 0], [0, 30], [-410, 30], [-410, 60]],
     "strokeColor": "#1e1e1e", "strokeWidth": 2,
     "label": "TextFrame", "labelFontSize": 13},

    {"type": "text", "id": "stage456L", "x": 24, "y": 784, "text": "Stages 4 - 5 - 6",
     "fontSize": 14, "strokeColor": "#6d28d9"},
    {"type": "text", "id": "stage456L2", "x": 24, "y": 802,
     "text": "translate, TTS, distribute", "fontSize": 12, "strokeColor": "#757575"},

    {"type": "rectangle", "id": "parallel", "x": 190, "y": 740, "width": 1120, "height": 340,
     "backgroundColor": "#eebefa", "strokeColor": "#8b5cf6", "strokeWidth": 2,
     "opacity": 40, "roundness": 3},
    {"type": "text", "id": "parallelT", "x": 210, "y": 750,
     "text": "ParallelPipeline   --   one branch per target language  (frame fan-out)",
     "fontSize": 17, "strokeColor": "#6d28d9"},

    {"type": "arrow", "id": "a_orch_par", "x": 750, "y": 710, "points": [[0, 0], [0, 30]],
     "strokeColor": "#1e1e1e", "strokeWidth": 2},

    # Hindi branch
    {"type": "rectangle", "id": "trHI", "x": 240, "y": 790, "width": 280, "height": 80,
     "backgroundColor": "#b2f2bb", "strokeColor": "#15803d", "strokeWidth": 2, "roundness": 3,
     "label": "TranslateProcessor -> HI\nOpenAI gpt-4o-mini"},
    {"type": "arrow", "id": "a_trHI_ttsHI", "x": 380, "y": 870, "points": [[0, 0], [0, 20]],
     "strokeColor": "#1e1e1e", "strokeWidth": 2,
     "startBinding": "trHI", "endBinding": "ttsHI"},
    {"type": "rectangle", "id": "ttsHI", "x": 240, "y": 890, "width": 280, "height": 80,
     "backgroundColor": "#ffc9c9", "strokeColor": "#b91c1c", "strokeWidth": 2, "roundness": 3,
     "label": "ElevenLabs TTS HI\nvoice_id=master  (same id)"},
    {"type": "arrow", "id": "a_ttsHI_outHI", "x": 380, "y": 970, "points": [[0, 0], [0, 20]],
     "strokeColor": "#1e1e1e", "strokeWidth": 2,
     "startBinding": "ttsHI", "endBinding": "outHI"},
    {"type": "rectangle", "id": "outHI", "x": 240, "y": 990, "width": 280, "height": 80,
     "backgroundColor": "#a5d8ff", "strokeColor": "#2563eb", "strokeWidth": 2, "roundness": 3,
     "label": "LiveKit output\n-> session-{id}-hi"},

    # Spanish branch
    {"type": "rectangle", "id": "trES", "x": 590, "y": 790, "width": 280, "height": 80,
     "backgroundColor": "#b2f2bb", "strokeColor": "#15803d", "strokeWidth": 2, "roundness": 3,
     "label": "TranslateProcessor -> ES\nOpenAI gpt-4o-mini"},
    {"type": "arrow", "id": "a_trES_ttsES", "x": 730, "y": 870, "points": [[0, 0], [0, 20]],
     "strokeColor": "#1e1e1e", "strokeWidth": 2,
     "startBinding": "trES", "endBinding": "ttsES"},
    {"type": "rectangle", "id": "ttsES", "x": 590, "y": 890, "width": 280, "height": 80,
     "backgroundColor": "#ffc9c9", "strokeColor": "#b91c1c", "strokeWidth": 2, "roundness": 3,
     "label": "ElevenLabs TTS ES\nvoice_id=master"},
    {"type": "arrow", "id": "a_ttsES_outES", "x": 730, "y": 970, "points": [[0, 0], [0, 20]],
     "strokeColor": "#1e1e1e", "strokeWidth": 2,
     "startBinding": "ttsES", "endBinding": "outES"},
    {"type": "rectangle", "id": "outES", "x": 590, "y": 990, "width": 280, "height": 80,
     "backgroundColor": "#a5d8ff", "strokeColor": "#2563eb", "strokeWidth": 2, "roundness": 3,
     "label": "LiveKit output\n-> session-{id}-es"},

    # French branch
    {"type": "rectangle", "id": "trFR", "x": 940, "y": 790, "width": 280, "height": 80,
     "backgroundColor": "#b2f2bb", "strokeColor": "#15803d", "strokeWidth": 2, "roundness": 3,
     "label": "TranslateProcessor -> FR\nOpenAI gpt-4o-mini"},
    {"type": "arrow", "id": "a_trFR_ttsFR", "x": 1080, "y": 870, "points": [[0, 0], [0, 20]],
     "strokeColor": "#1e1e1e", "strokeWidth": 2,
     "startBinding": "trFR", "endBinding": "ttsFR"},
    {"type": "rectangle", "id": "ttsFR", "x": 940, "y": 890, "width": 280, "height": 80,
     "backgroundColor": "#ffc9c9", "strokeColor": "#b91c1c", "strokeWidth": 2, "roundness": 3,
     "label": "ElevenLabs TTS FR\nvoice_id=master"},
    {"type": "arrow", "id": "a_ttsFR_outFR", "x": 1080, "y": 970, "points": [[0, 0], [0, 20]],
     "strokeColor": "#1e1e1e", "strokeWidth": 2,
     "startBinding": "ttsFR", "endBinding": "outFR"},
    {"type": "rectangle", "id": "outFR", "x": 940, "y": 990, "width": 280, "height": 80,
     "backgroundColor": "#a5d8ff", "strokeColor": "#2563eb", "strokeWidth": 2, "roundness": 3,
     "label": "LiveKit output\n-> session-{id}-fr"},

    {"type": "text", "id": "branchN", "x": 1335, "y": 900, "text": "...",
     "fontSize": 40, "strokeColor": "#8b5cf6"},
    {"type": "text", "id": "branchN2", "x": 1330, "y": 960, "text": "N langs",
     "fontSize": 15, "strokeColor": "#6d28d9"},

    {"type": "arrow", "id": "a_master_lkin", "x": 415, "y": 290, "points": [[0, 0], [0, 160]],
     "strokeColor": "#2563eb", "strokeWidth": 2,
     "label": "audio frames", "labelFontSize": 13,
     "startBinding": "masterRoom", "endBinding": "lkin"},

    # ---- External services zone ----
    {"type": "rectangle", "id": "zoneExt", "x": 10, "y": 1110, "width": 1480, "height": 150,
     "backgroundColor": "#ffd8a8", "strokeColor": "#c2410c", "strokeWidth": 1,
     "opacity": 35, "roundness": 3},
    {"type": "text", "id": "zoneExtL", "x": 24, "y": 1118, "text": "External services",
     "fontSize": 17, "strokeColor": "#9a3412"},

    {"type": "rectangle", "id": "dgApi", "x": 300, "y": 1150, "width": 260, "height": 90,
     "backgroundColor": "#ffd8a8", "strokeColor": "#c2410c", "strokeWidth": 2, "roundness": 3,
     "label": "Deepgram\nstreaming WebSocket\napi.deepgram.com"},
    {"type": "rectangle", "id": "oaApi", "x": 620, "y": 1150, "width": 260, "height": 90,
     "backgroundColor": "#ffd8a8", "strokeColor": "#c2410c", "strokeWidth": 2, "roundness": 3,
     "label": "OpenAI\nchat.completions\ngpt-4o-mini"},
    {"type": "rectangle", "id": "elApi", "x": 940, "y": 1150, "width": 260, "height": 90,
     "backgroundColor": "#ffd8a8", "strokeColor": "#c2410c", "strokeWidth": 2, "roundness": 3,
     "label": "ElevenLabs\nstreaming TTS  +  IVC\napi.elevenlabs.io"},

    {"type": "arrow", "id": "a_stt_dg", "x": 910, "y": 540,
     "points": [[0, 0], [0, 560], [-480, 560], [-480, 610]],
     "strokeColor": "#c2410c", "strokeWidth": 1, "strokeStyle": "dashed",
     "label": "audio in / text out", "labelFontSize": 12},
    {"type": "arrow", "id": "a_tr_oa", "x": 730, "y": 830, "points": [[0, 0], [0, 320]],
     "strokeColor": "#c2410c", "strokeWidth": 1, "strokeStyle": "dashed",
     "label": "prompt", "labelFontSize": 12},
    {"type": "arrow", "id": "a_tts_el", "x": 1080, "y": 930, "points": [[0, 0], [0, 220]],
     "strokeColor": "#c2410c", "strokeWidth": 1, "strokeStyle": "dashed",
     "label": "text / audio", "labelFontSize": 12},
    {"type": "arrow", "id": "a_api_el", "x": 770, "y": 330,
     "points": [[0, 0], [300, 820]],
     "strokeColor": "#f59e0b", "strokeWidth": 1, "strokeStyle": "dashed",
     "label": "voice/clone -> IVC", "labelFontSize": 12},

    # ---- Per-language LiveKit rooms zone ----
    {"type": "rectangle", "id": "zoneRooms", "x": 10, "y": 1290, "width": 1480, "height": 160,
     "backgroundColor": "#c3fae8", "strokeColor": "#0e7490", "strokeWidth": 1,
     "opacity": 40, "roundness": 3},
    {"type": "text", "id": "zoneRoomsL", "x": 24, "y": 1300,
     "text": "LiveKit per-language rooms   (subscribers join with subscribe-only JWT)",
     "fontSize": 17, "strokeColor": "#0e7490"},

    {"type": "rectangle", "id": "rmHI", "x": 240, "y": 1335, "width": 280, "height": 100,
     "backgroundColor": "#c3fae8", "strokeColor": "#0e7490", "strokeWidth": 2, "roundness": 3,
     "label": "LiveKit room\nsession-{id}-hi"},
    {"type": "rectangle", "id": "rmES", "x": 590, "y": 1335, "width": 280, "height": 100,
     "backgroundColor": "#c3fae8", "strokeColor": "#0e7490", "strokeWidth": 2, "roundness": 3,
     "label": "LiveKit room\nsession-{id}-es"},
    {"type": "rectangle", "id": "rmFR", "x": 940, "y": 1335, "width": 280, "height": 100,
     "backgroundColor": "#c3fae8", "strokeColor": "#0e7490", "strokeWidth": 2, "roundness": 3,
     "label": "LiveKit room\nsession-{id}-fr"},

    {"type": "arrow", "id": "a_outHI_rm", "x": 380, "y": 1070, "points": [[0, 0], [0, 265]],
     "strokeColor": "#2563eb", "strokeWidth": 2,
     "label": "published audio", "labelFontSize": 12,
     "startBinding": "outHI", "endBinding": "rmHI"},
    {"type": "arrow", "id": "a_outES_rm", "x": 730, "y": 1070, "points": [[0, 0], [0, 265]],
     "strokeColor": "#2563eb", "strokeWidth": 2,
     "startBinding": "outES", "endBinding": "rmES"},
    {"type": "arrow", "id": "a_outFR_rm", "x": 1080, "y": 1070, "points": [[0, 0], [0, 265]],
     "strokeColor": "#2563eb", "strokeWidth": 2,
     "startBinding": "outFR", "endBinding": "rmFR"},

    # ---- Audience zone ----
    {"type": "rectangle", "id": "zoneAud", "x": 10, "y": 1450, "width": 1480, "height": 160,
     "backgroundColor": "#dbe4ff", "strokeColor": "#2563eb", "strokeWidth": 1,
     "opacity": 35, "roundness": 3},
    {"type": "text", "id": "zoneAudL", "x": 24, "y": 1460,
     "text": "Audience devices  (clients/listener.html, subscribe-only LiveKit JWT)",
     "fontSize": 17, "strokeColor": "#2563eb"},

    {"type": "rectangle", "id": "audHI", "x": 260, "y": 1495, "width": 240, "height": 90,
     "backgroundColor": "#a5d8ff", "strokeColor": "#2563eb", "strokeWidth": 2, "roundness": 3,
     "label": "Hindi listeners\nlistener.html?lang=hi"},
    {"type": "rectangle", "id": "audES", "x": 610, "y": 1495, "width": 240, "height": 90,
     "backgroundColor": "#a5d8ff", "strokeColor": "#2563eb", "strokeWidth": 2, "roundness": 3,
     "label": "Spanish listeners\nlistener.html?lang=es"},
    {"type": "rectangle", "id": "audFR", "x": 960, "y": 1495, "width": 240, "height": 90,
     "backgroundColor": "#a5d8ff", "strokeColor": "#2563eb", "strokeWidth": 2, "roundness": 3,
     "label": "French listeners\nlistener.html?lang=fr"},

    {"type": "arrow", "id": "a_rmHI_audHI", "x": 380, "y": 1435, "points": [[0, 0], [0, 60]],
     "strokeColor": "#15803d", "strokeWidth": 2, "label": "sub", "labelFontSize": 12,
     "startBinding": "rmHI", "endBinding": "audHI"},
    {"type": "arrow", "id": "a_rmES_audES", "x": 730, "y": 1435, "points": [[0, 0], [0, 60]],
     "strokeColor": "#15803d", "strokeWidth": 2,
     "startBinding": "rmES", "endBinding": "audES"},
    {"type": "arrow", "id": "a_rmFR_audFR", "x": 1080, "y": 1435, "points": [[0, 0], [0, 60]],
     "strokeColor": "#15803d", "strokeWidth": 2,
     "startBinding": "rmFR", "endBinding": "audFR"},

    {"type": "text", "id": "audNote", "x": 1240, "y": 1525, "text": "...up to N audiences",
     "fontSize": 15, "strokeColor": "#6d28d9"},

    {"type": "arrow", "id": "a_aud_api", "x": 380, "y": 1495,
     "points": [[0, 0], [0, -30], [290, -30], [290, -1325]],
     "strokeColor": "#f59e0b", "strokeWidth": 1, "strokeStyle": "dashed",
     "label": "GET /session  -> token", "labelFontSize": 12},

    # ---- Frame-types legend ----
    {"type": "rectangle", "id": "legend", "x": 1240, "y": 620, "width": 250, "height": 210,
     "backgroundColor": "#fff3bf", "strokeColor": "#92400e", "strokeWidth": 1,
     "roundness": 3, "opacity": 85},
    {"type": "text", "id": "legT", "x": 1252, "y": 628,
     "text": "Frame types in the pipeline", "fontSize": 14, "strokeColor": "#92400e"},
    {"type": "text", "id": "legf1", "x": 1252, "y": 654,
     "text": "AudioRawFrame   16 kHz mono", "fontSize": 12},
    {"type": "text", "id": "legf2", "x": 1252, "y": 676,
     "text": "InterimTranscriptionFrame   churn", "fontSize": 12, "strokeColor": "#757575"},
    {"type": "text", "id": "legf3", "x": 1252, "y": 698,
     "text": "TranscriptionFrame   is_final = True", "fontSize": 12},
    {"type": "text", "id": "legf4", "x": 1252, "y": 720,
     "text": "TextFrame   stable phrase", "fontSize": 12, "strokeColor": "#15803d"},
    {"type": "text", "id": "legf5", "x": 1252, "y": 742,
     "text": "TTSAudioRawFrame   24 kHz", "fontSize": 12, "strokeColor": "#b91c1c"},
    {"type": "text", "id": "legf6", "x": 1252, "y": 764,
     "text": "OutputAudioRawFrame   to LiveKit", "fontSize": 12, "strokeColor": "#2563eb"},
    {"type": "text", "id": "legf7", "x": 1252, "y": 792,
     "text": "orchestrator filters interim,", "fontSize": 12},
    {"type": "text", "id": "legf8", "x": 1252, "y": 810,
     "text": "converts final  ->  TextFrame", "fontSize": 12},
]


# ----------- conversion to canonical Excalidraw scene format -----------

FONT_VIRGIL = 1  # Excalidraw's default hand-drawn font
FONT_NORMAL = 5  # Excalidraw's "Excalifont"


def nonce() -> int:
    return random.randint(1, 2**31 - 1)


def base_props(el: dict) -> dict:
    return {
        "id": el["id"],
        "x": el.get("x", 0),
        "y": el.get("y", 0),
        "width": el.get("width", 0),
        "height": el.get("height", 0),
        "angle": 0,
        "strokeColor": el.get("strokeColor", "#1e1e1e"),
        "backgroundColor": el.get("backgroundColor", "transparent"),
        "fillStyle": el.get("fillStyle", "solid"),
        "strokeWidth": el.get("strokeWidth", 2),
        "strokeStyle": el.get("strokeStyle", "solid"),
        "roughness": 1,
        "opacity": el.get("opacity", 100),
        "groupIds": [],
        "frameId": None,
        "roundness": ({"type": el["roundness"]} if el.get("roundness") else None),
        "seed": nonce(),
        "version": 1,
        "versionNonce": nonce(),
        "isDeleted": False,
        "boundElements": [],
        "updated": 1,
        "link": None,
        "locked": False,
    }


def text_element(
    *, eid: str, x: float, y: float, text: str, font_size: int = 16,
    stroke_color: str = "#1e1e1e", container_id: str | None = None,
    width: float | None = None, height: float | None = None,
) -> dict:
    # rough width estimate for unbound text labels
    w = width if width is not None else max(20, len(text) * font_size * 0.55)
    h = height if height is not None else font_size * 1.25 * (text.count("\n") + 1)
    return {
        **base_props({
            "id": eid, "x": x, "y": y, "width": w, "height": h,
            "strokeColor": stroke_color,
        }),
        "type": "text",
        "fontSize": font_size,
        "fontFamily": FONT_NORMAL,
        "text": text,
        "textAlign": "center" if container_id else "left",
        "verticalAlign": "middle" if container_id else "top",
        "containerId": container_id,
        "originalText": text,
        "autoResize": True,
        "lineHeight": 1.25,
    }


def convert(simple: list[dict]) -> list[dict]:
    out: list[dict] = []
    by_id: dict[str, dict] = {}

    for el in simple:
        if el["type"] == "rectangle":
            r = {
                **base_props(el),
                "type": "rectangle",
            }
            out.append(r)
            by_id[el["id"]] = r
            if el.get("label"):
                tid = el["id"] + "_lbl"
                t = text_element(
                    eid=tid,
                    x=el["x"] + 10,
                    y=el["y"] + 10,
                    text=el["label"],
                    font_size=el.get("labelFontSize", 16),
                    container_id=el["id"],
                    width=el["width"] - 20,
                    height=el["height"] - 20,
                )
                t["textAlign"] = "center"
                t["verticalAlign"] = "middle"
                out.append(t)
                r["boundElements"].append({"type": "text", "id": tid})

        elif el["type"] == "text":
            t = text_element(
                eid=el["id"],
                x=el["x"],
                y=el["y"],
                text=el["text"],
                font_size=el.get("fontSize", 16),
                stroke_color=el.get("strokeColor", "#1e1e1e"),
            )
            out.append(t)
            by_id[el["id"]] = t

        elif el["type"] == "arrow":
            pts = el["points"]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            w = max(xs) - min(xs)
            h = max(ys) - min(ys)
            a = {
                **base_props({
                    "id": el["id"],
                    "x": el["x"], "y": el["y"],
                    "width": w if w != 0 else 1,
                    "height": h if h != 0 else 1,
                    "strokeColor": el.get("strokeColor", "#1e1e1e"),
                    "strokeWidth": el.get("strokeWidth", 2),
                    "strokeStyle": el.get("strokeStyle", "solid"),
                }),
                "type": "arrow",
                "points": pts,
                "lastCommittedPoint": None,
                "startBinding": (
                    {"elementId": el["startBinding"], "focus": 0, "gap": 4}
                    if el.get("startBinding") else None
                ),
                "endBinding": (
                    {"elementId": el["endBinding"], "focus": 0, "gap": 4}
                    if el.get("endBinding") else None
                ),
                "startArrowhead": None,
                "endArrowhead": "arrow",
                "elbowed": False,
            }
            out.append(a)
            by_id[el["id"]] = a
            if el.get("label"):
                tid = el["id"] + "_lbl"
                t = text_element(
                    eid=tid,
                    x=el["x"] + w / 2,
                    y=el["y"] + h / 2,
                    text=el["label"],
                    font_size=el.get("labelFontSize", 14),
                    container_id=el["id"],
                )
                t["textAlign"] = "center"
                t["verticalAlign"] = "middle"
                out.append(t)
                a["boundElements"].append({"type": "text", "id": tid})

    # populate boundElements for shape <- arrow bindings
    for el in simple:
        if el["type"] != "arrow":
            continue
        for end in ("startBinding", "endBinding"):
            target = el.get(end)
            if target and target in by_id:
                target_el = by_id[target]
                target_el.setdefault("boundElements", []).append(
                    {"type": "arrow", "id": el["id"]}
                )

    return out


def upload_to_excalidraw(scene_json: str) -> str:
    """Encrypt scene with AES-GCM and POST to excalidraw's share backend.
    Returns a public URL of the form https://excalidraw.com/#json={id},{key}.
    """
    import base64
    import os
    import httpx
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = os.urandom(16)
    iv = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(iv, scene_json.encode("utf-8"), None)
    payload = iv + ciphertext

    resp = httpx.post(
        "https://json.excalidraw.com/api/v2/post/",
        content=payload,
        headers={"Content-Type": "application/octet-stream"},
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    diagram_id = body["id"]
    key_b64 = base64.urlsafe_b64encode(key).rstrip(b"=").decode()
    return f"https://excalidraw.com/#json={diagram_id},{key_b64}"


def main() -> None:
    elements = convert(SIMPLE)
    scene = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {
            "gridSize": 20,
            "viewBackgroundColor": "#ffffff",
        },
        "files": {},
    }
    out_path = Path(__file__).parent / "architecture.excalidraw"
    out_path.write_text(json.dumps(scene, indent=2))
    compact_str = json.dumps(scene, separators=(",", ":"))
    print(f"wrote {out_path}  ({len(elements)} elements, {len(compact_str)} bytes compact)")
    try:
        url = upload_to_excalidraw(compact_str)
        print(f"shareable URL: {url}")
    except Exception as exc:
        print(f"upload failed: {exc!r}")


if __name__ == "__main__":
    main()
