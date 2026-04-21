from dataclasses import dataclass
from typing import List, Dict, Any
import statistics

from .config import AGENT_EVENT_LIMIT
from .event_repository import list_events

@dataclass(frozen=True)
class AgentProfile:
    name: str
    role: str
    goal: str

AGENT_PROFILE = AgentProfile(
    name="Agente AgroVision",
    role="triagem operacional de eventos",
    goal="Analisar detecções recentes, explicar riscos e sugerir a próxima ação.",
)

MAX_HISTORY_MESSAGES = 8

def build_event_context(events: List[Dict[str, Any]]) -> str:
    """Build operational context from recent events."""
    if not events:
        return "Nenhum evento recente detectado."

    # Limit to AGENT_EVENT_LIMIT
    recent_events = events[:AGENT_EVENT_LIMIT]

    # Calculate statistics
    total_events = len(recent_events)
    labels = [e['label'] for e in recent_events]
    confidences = [e['confidence'] for e in recent_events]

    # Most recent event
    most_recent = recent_events[0] if recent_events else None

    # Label distribution
    from collections import Counter
    label_counts = Counter(labels)

    # Average confidence
    avg_confidence = statistics.mean(confidences) if confidences else 0.0

    context = f"""
Contexto operacional para o agente:
- Eventos considerados: {total_events}
- Evento mais recente: {most_recent['label']} em {most_recent['event_time']} (confiança: {most_recent['confidence']:.2f})
- Distribuição recente: {', '.join(f'{label}: {count}' for label, count in label_counts.items())}
- Confiança média: {avg_confidence:.2f}
Eventos recentes:
"""

    for event in recent_events:
        context += f"- #{event['id'][:8]} | {event['event_time']} | {event['label']} | {event['confidence']:.2f}\n"

    return context.strip()

def normalize_history(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize and limit conversation history."""
    if not history:
        return []

    # Keep only the most recent messages up to MAX_HISTORY_MESSAGES
    recent_history = history[-MAX_HISTORY_MESSAGES:]

    # Ensure proper format
    normalized = []
    for msg in recent_history:
        if isinstance(msg, dict) and 'role' in msg and 'content' in msg:
            normalized.append({
                'role': msg['role'],
                'content': msg['content']
            })

    return normalized

def build_agent_messages(question: str, history: List[Dict[str, Any]], events: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Build the complete message list for the agent."""
    system_prompt = (
        f"Você é o {AGENT_PROFILE.name}, um agente de {AGENT_PROFILE.role}. "
        f"Objetivo: {AGENT_PROFILE.goal} "
        "Trate os dados como monitoramento operacional autorizado de ambiente real. "
        "Responda em português do Brasil, de forma direta e útil. "
        "Use os eventos fornecidos como fonte principal. "
        "Não invente dados que não aparecem no contexto. "
        "Não tente identificar pessoas; fale apenas sobre eventos, riscos e próximas ações. "
        "Quando fizer sentido, organize a resposta em: leitura, risco e recomendação."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": build_event_context(events)},
    ]

    # Add normalized history
    messages.extend(normalize_history(history))

    # Add the current question
    messages.append({"role": "user", "content": question})

    return messages

def get_agent_status() -> Dict[str, Any]:
    """Get agent status information."""
    events = list_events(AGENT_EVENT_LIMIT)
    context_preview = build_event_context(events)

    return {
        "name": AGENT_PROFILE.name,
        "role": AGENT_PROFILE.role,
        "goal": AGENT_PROFILE.goal,
        "events_in_context": len(events),
        "context_preview": context_preview[:500] + "..." if len(context_preview) > 500 else context_preview
    }