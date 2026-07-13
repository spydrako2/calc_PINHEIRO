"""
Versão e histórico de atualizações do HoleritePRO.

Exibidos na interface (rodapé do cabeçalho e seção "Novidades"). O texto do
CHANGELOG é escrito em linguagem simples, para o usuário final — sem jargão
técnico. Ao lançar uma nova versão: incremente VERSION e adicione uma entrada
no topo do CHANGELOG.
"""

VERSION = "1.0"

# Histórico em linguagem do usuário — mais recente primeiro.
# Cada entrada: (versão, data_amigavel, [lista de mudanças]).
CHANGELOG = [
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
