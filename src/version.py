"""
Versão e histórico de atualizações do HoleritePRO.

Exibidos na interface (rodapé do cabeçalho e seção "Novidades"). O texto do
CHANGELOG é escrito em linguagem simples, para o usuário final — sem jargão
técnico.

VERSION é o rótulo de versão (bump manual, só em marcos relevantes). BUILD é
o número de commits do repositório, lido automaticamente a cada execução —
muda sozinho a cada novo commit, então nunca fica "desatualizado" no app.

Ao lançar uma novidade visível ao usuário: adicione uma entrada no topo do
CHANGELOG (a interface mostra só as mais recentes).
"""

import subprocess
from pathlib import Path

VERSION = "1.0"


def _build_number() -> str:
    """Quantidade de commits no repositório — cresce a cada commit novo."""
    root = Path(__file__).resolve().parent.parent
    try:
        out = subprocess.check_output(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=str(root), stderr=subprocess.DEVNULL, timeout=3,
        ).decode().strip()
        if out.isdigit():
            return out
    except Exception:
        pass
    return "dev"


BUILD = _build_number()

# Histórico em linguagem do usuário — mais recente primeiro.
# Cada entrada: (versão, data_amigavel, [lista de mudanças]).
CHANGELOG = [
    (
        "1.0",
        "Julho/2026",
        [
            "Tese CHS: quando o holerite de aposentado não informa a jornada, "
            "a planilha agora avisa com destaque colorido em vez de mostrar "
            "valor zerado sem explicação.",
            "Planilha da CHS pronta para impressão em uma página, no formato "
            "paisagem — igual à planilha do Piso Salarial Docente.",
        ],
    ),
    (
        "1.0",
        "Julho/2026",
        [
            "Primeira versão oficial do HoleritePRO.",
            "Leitura automática dos holerites em PDF (folhas do Estado de SP e da "
            "aposentadoria).",
            "Teses disponíveis: Piso Salarial Docente, Acúmulo IAMSPE, "
            "Gratificações APEOESP e CHS sobre o Piso Docente.",
            "Cálculo da CHS considerando também a carga de Coordenador/Vice-Diretor.",
            "Consolidação de valores atrasados/retroativos, destacados em amarelo "
            "na planilha.",
            "Mensagens claras quando o PDF não é reconhecido ou quando a tese "
            "escolhida não bate com os holerites.",
            "Geração da planilha de cálculo em Excel pronta para download.",
        ],
    ),
]

# Quantas entradas do histórico aparecem no expander "Novidades" da interface.
CHANGELOG_VISIVEL = 3
