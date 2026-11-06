"""Apply review decisions consistently to text and original-text highlights."""
from app.models.schemas import Detection


def resolve_intervals(text: str, detections: list[Detection], confirmed_only: bool = False) -> list[dict]:
    """Keep overlap coverage, taking metadata from the latest manual decision.

    Stable sorting retains historical ties: earliest start, longest interval,
    then detection/position list order. Adjacent intervals stay separate.
    Input positions and identity memberships are never edited.
    """
    ranges = []
    for detection in detections:
        if not detection.enabled:
            continue
        if confirmed_only and not (detection.cluster_confirmed or detection.user_added
                                   or getattr(detection, '_force_apply', False)):
            continue
        for position in detection.positions:
            if not 0 <= position.start < position.end <= len(text):
                raise ValueError('Posición de anonimización inválida')
            ranges.append({
                'start': position.start, 'end': position.end,
                'cat': detection.cat, 'placeholder': detection.placeholder,
                'cluster_id': detection.cluster_id, 'manual_order': detection.manual_order,
            })
    ranges.sort(key=lambda item: (item['start'], -item['end']))
    resolved = []
    for item in ranges:
        if resolved and item['start'] < resolved[-1]['end']:
            component = resolved[-1]
            component['end'] = max(component['end'], item['end'])
            if item['manual_order'] > component['manual_order']:
                for key in ('cat', 'placeholder', 'cluster_id', 'manual_order'):
                    component[key] = item[key]
        else:
            resolved.append(item.copy())
    return resolved


def anonymize_text(text: str, detections: list[Detection], confirmed_only: bool = False) -> str:
    out = text
    for interval in reversed(resolve_intervals(text, detections, confirmed_only)):
        out = out[:interval['start']] + interval['placeholder'] + out[interval['end']:]
    return out


def build_highlights(text: str, detections: list[Detection]) -> list[dict]:
    """Return the same resolved components used by anonymization."""
    return resolve_intervals(text, detections)
