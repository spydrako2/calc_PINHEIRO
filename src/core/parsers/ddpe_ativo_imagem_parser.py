"""
Parser para holerites DDPE de servidores ativos em PDF somente-imagem.

Holerites capturados via app mobile geram PDFs com páginas JPEG sem camada
de texto. Este parser:
1. Detecta o template pelo OCR + marcadores específicos do app SP Gov.
2. Limpa ruídos típicos do OCR (bordas de tabela, confusão letra/dígito).
3. Sobrescreve extratores de cabeçalho para tolerar ruído OCR.
4. Delega o parse de verbas ao DDPEParser após a limpeza.
"""

import re
from typing import List, Optional

from src.core.parsers.ddpe_parser import DDPEParser
from src.core.pdf_reader import PaginaExtraida
from src.core.data_model import Holerite


class DDPEAtivoImagemParser(DDPEParser):
    """
    Parser para holerites DDPE (ativo) extraídos de PDF somente-imagem via OCR.

    Herda toda a lógica de extração do DDPEParser; acrescenta:
    - Detecção específica para texto OCR (marcadores do app mobile SP Gov)
    - Limpeza de ruídos de OCR antes de passar ao parser pai
    - Extratores de CPF e nome tolerantes a ruído OCR
    """

    # Marcadores presentes em screenshots do app Contracheque SP Gov
    _MOBILE_MARKERS = [
        r"Baixar\s+PDF",
        r"P[áa]gina\s+inicial",
        r"Contracheque",
        r"Demonstrativo\s+de\s+Pagamento",  # lowercase — nunca aparece assim no PDF texto
    ]

    # Linhas de UI mobile a descartar (barra de status, navegação inferior)
    _UI_NOISE_PATTERNS = [
        r"^\d{2}:\d{2}",           # hora do celular (ex: "22:45")
        r"Baixar\s+PDF",
        r"P[áa]gina\s+inicial",
        r"Notifica[çc][õo]es",
        r"Servi[çc]os",
        r"^\s*Mais\s*$",
        r"^\s*[<>]\s*$",           # setas de navegação
        r"^\s*[●○•·]\s*$",         # pontos de paginação
    ]

    def detect_template(self, texto: str) -> bool:
        """
        Detecta holerites DDPE vindos de PDF somente-imagem.

        Requer tanto as palavras-chave DDPE quanto pelo menos um marcador
        do app mobile — evitando conflito com DDPEParser em PDFs normais.
        """
        if not super().detect_template(texto):
            return False
        return any(
            re.search(p, texto, re.IGNORECASE) for p in self._MOBILE_MARKERS
        )

    def parse(self, paginas: List[PaginaExtraida]) -> Holerite:
        """Limpa texto OCR e delega ao parser pai."""
        paginas_limpas = [
            PaginaExtraida(
                numero=p.numero,
                texto=self._clean_ocr(p.texto),
                metodo=p.metodo,
                confianca=p.confianca,
            )
            for p in paginas
        ]
        return super().parse(paginas_limpas)

    def _extract_cabecalho(self):
        """
        Override: extração de cabeçalho tolerante a OCR.
        CPF vazio não bloqueia — OCR de imagem fragmenta dados numéricos.
        """
        from src.core.data_model import CabecalhoHolerite, TemplateType, TipoFolha

        if not self.paginas:
            raise ValueError("No pages provided")

        texto = self.get_first_page_text()

        cpf = self._extract_cpf(texto) or ""
        nome = self._extract_nome_ddpe(texto) or self._extract_field(texto, "nome")
        if not nome:
            raise ValueError("Nome not found in holerite")

        cargo = self._extract_cargo_ddpe(texto) or self._extract_field(texto, "cargo")
        unidade = self._extract_unidade_ddpe(texto) or self._extract_field(texto, "unidade")
        competencia = self._extract_competencia_ddpe(texto) or self._extract_field(texto, "competencia")
        data_pagamento = self._extract_data_pagamento_ddpe(texto) or self._extract_field(texto, "data_pagamento")

        if competencia:
            competencia = self._normalize_date(competencia, "AAAA-MM")

        tipo_folha = self._extract_tipo_folha(texto)

        cabecalho = CabecalhoHolerite(
            nome=nome.strip(),
            cpf=cpf.strip() if cpf else "OCR-INDISPONIVEL",
            cargo=cargo.strip() if cargo else None,
            unidade=unidade.strip() if unidade else None,
            competencia=competencia or "",
            tipo_folha=tipo_folha,
            data_pagamento=data_pagamento.strip() if data_pagamento else None,
            template_type=TemplateType.DDPE,
        )

        self.extracted_cabecalho = cabecalho
        return cabecalho

    # ------------------------------------------------------------------ #
    # Extratores de cabeçalho — tolerância a ruído OCR                    #
    # ------------------------------------------------------------------ #

    def _extract_cpf(self, texto: str) -> Optional[str]:
        """
        Extrai CPF do texto OCR do holerite imagem.

        O header DDPE em imagem coloca Nome/Reg/CPF numa única linha
        garbled. Estratégias em cascata:
        1. Padrão formatado XXX.XXX.XXX-XX
        2. Padrão DDPE compacto XXXXXXXXX/XX
        3. Qualquer sequência de 11 dígitos consecutivos (OCR sem formatação)
        4. Juntar dígitos espalhados na linha do nome (OCR fragmentou CPF)
        5. Sequência de 10 dígitos nas primeiras linhas (OCR perdeu 1 dígito)
        """
        # Estratégia 1 e 2: padrões já suportados pelo pai
        result = super()._extract_cpf(texto)
        if result:
            return result

        # Estratégia 3: 11 dígitos consecutivos (sem ponto/traço — OCR omitiu)
        m = re.search(r'\b(\d{11})\b', texto)
        if m:
            return self._normalize_cpf(m.group(1))

        # Estratégia 4: Juntar dígitos espalhados na linha do nome
        # OCR do ABIMAEL produz: "ABIMAEL DE CAMPOS NETO DB 65 . 7100 00071 8108802 1 12270700A"
        # O CPF DDPE (9dig/2dig = 11 dígitos) está fragmentado com espaços e letras
        linhas = texto.split("\n")
        for linha in linhas[:15]:
            # Procurar linhas que parecem ter nome + dados de registro + CPF
            # (linha longa com maiúsculas + muitos dígitos espalhados)
            all_digits = re.findall(r'\d', linha)
            if len(all_digits) >= 11:
                # Extrair todos os dígitos da parte após o nome
                # Nome = sequência de palavras maiúsculas com >= 3 letras
                nome_match = re.match(
                    r'^([A-ZÁÉÍÓÚÂÃÕÊÔÇÀ][A-ZÁÉÍÓÚÂÃÕÊÔÇÀ\s]+?)\s+(?=[A-Z]{1,2}\s+\d|[A-Z]\s+[a-z]|\d)',
                    linha
                )
                if nome_match:
                    after_nome = linha[nome_match.end():]
                else:
                    after_nome = linha

                digits_after = ''.join(re.findall(r'\d', after_nome))
                if len(digits_after) >= 11:
                    # Últimos 11 dígitos = CPF no layout DDPE (Reg + Sistema vêm antes)
                    cpf_digits = digits_after[-11:]
                    return self._normalize_cpf(cpf_digits)

        # Estratégia 5: 10 dígitos nas primeiras 10 linhas (dígito verificador perdido no OCR)
        for linha in linhas[:10]:
            m = re.search(r'\b(\d{10})\b', linha)
            if m:
                digits = m.group(1) + "0"
                return self._normalize_cpf(digits)

        return None

    # Headers institucionais — nunca são nomes de pessoas
    _INSTITUTIONAL_BLACKLIST = [
        "GOVERNO", "ESTADO", "DEPARTAMENTO", "DESPESA", "PESSOAL",
        "DEMONSTRATIVO", "PAGAMENTO", "SECRETARIA", "PAULO",
    ]

    def _extract_nome_ddpe(self, texto: str) -> Optional[str]:
        """
        Extrai nome de holerites OCR.

        No texto OCR o header coloca o nome em MAIÚSCULAS numa linha com
        códigos de registro e CPF. Estratégias:
        1. Método pai (layout padrão "Nome Reg." como header)
        2. Palavras consecutivas em MAIÚSCULAS com >= 3 letras cada
           (ignora tokens curtos tipo "DB", "D", "m." que são ruído OCR)
           Exclui linhas que são headers institucionais (GOVERNO, DEPARTAMENTO, etc.)
        """
        # Tentar método pai primeiro (layout padrão)
        result = super()._extract_nome_ddpe(texto)
        if result:
            return result

        # Fallback OCR: extrair palavras maiúsculas consecutivas (>= 3 letras)
        linhas = texto.split("\n")
        for linha in linhas[:15]:
            linha = linha.strip()
            if not linha:
                continue

            # Pular headers institucionais
            linha_upper = linha.upper()
            if any(bl in linha_upper for bl in self._INSTITUTIONAL_BLACKLIST):
                continue

            # Tokenizar e coletar palavras que parecem ser nome próprio
            tokens = linha.split()
            nome_palavras = []
            for token in tokens:
                letras = re.sub(r'[^A-ZÁÉÍÓÚÂÃÕÊÔÇÀa-záéíóúâãõêô]', '', token)
                is_upper = token == token.upper() and len(letras) >= 2
                if is_upper and len(letras) >= 3:
                    nome_palavras.append(token)
                elif is_upper and len(letras) == 2 and len(nome_palavras) >= 1:
                    if token.upper() in {"DE", "DA", "DO", "DAS", "DOS"}:
                        nome_palavras.append(token)
                    else:
                        break
                elif nome_palavras:
                    break

            if len(nome_palavras) >= 2:
                nome_candidato = " ".join(nome_palavras)
                letras_total = re.sub(r'[^A-ZÁÉÍÓÚÂÃÕÊÔÇÀa-záéíóúâãõêô]', '', nome_candidato)
                if len(letras_total) >= 5:
                    return nome_candidato

        return None

    def _extract_competencia_ddpe(self, texto: str) -> Optional[str]:
        """
        Extrai competência de holerites OCR.

        No OCR o padrão 'Tipo da Folha...' pode estar garbled.
        Busca MM/YYYY em linhas que contenham 'NORMAL', 'FOLHA' ou 'DDA'.
        """
        # Tentar método pai primeiro
        result = super()._extract_competencia_ddpe(texto)
        if result:
            return result

        # Fallback OCR: linha com FOLHA/NORMAL + padrão de data
        for linha in texto.split("\n"):
            if re.search(r'FOLHA|NORMAL|DDA', linha, re.IGNORECASE):
                m = re.search(r'(\d{2}/\d{4})', linha)
                if m:
                    return m.group(1)
                # OCR pode omitir a barra: "072021" → "07/2021"
                m = re.search(r'\b(\d{2})(\d{4})\b', linha)
                if m and 1 <= int(m.group(1)) <= 12 and int(m.group(2)) >= 2000:
                    return f"{m.group(1)}/{m.group(2)}"

        # Busca genérica por padrão de competência em todo o texto
        for linha in texto.split("\n"):
            m = re.search(r'\b(\d{2}/\d{4})\b', linha)
            if m:
                mes, ano = m.group(1).split('/')
                if 1 <= int(mes) <= 12 and int(ano) >= 2000:
                    return m.group(1)

        return None

    # ------------------------------------------------------------------ #
    # Extração de totais — tolerante a OCR sem formatação decimal         #
    # ------------------------------------------------------------------ #

    def _parse_totals_from_page(self, texto: str):
        """
        Extrai totais de página OCR.

        OCR frequentemente garble 'Descontos' → 'Descorios' e omite
        pontos/vírgulas dos valores. Estratégias:
        1. Tenta o método pai (números com vírgula)
        2. Fallback OCR: busca linha com RPPE/RGPS + sequências de dígitos
        """
        # Estratégia 1: método pai (espera números com vírgula)
        result = super()._parse_totals_from_page(texto)
        if result:
            return result

        # Estratégia 2: linha "RPPE / RGPS D1 D2 D3" — valores sem formatação
        # O layout DDPE imagem tem: "RPPE / RGPS | FGTS | Sal.Contrib | Descontos | Líquido"
        m = re.search(
            r'(?:RPPE|RGPS|INPS|RGSP).*?(\d{4,8})[\s,]+(\d{3,8})[\s,]+(\d{4,8})',
            texto, re.IGNORECASE
        )
        if m:
            # Tentar interpretar os 3 números como: descontos, ?, liquido
            # ou como: fgts_base, descontos, liquido
            nums = [self._parse_ocr_valor(m.group(i)) for i in (1, 2, 3)]
            # Verificar tripla (V, D, L) onde V - D ≈ L com tolerância maior
            for i in range(len(nums)):
                for j in range(len(nums)):
                    if j == i:
                        continue
                    for k in range(len(nums)):
                        if k == i or k == j:
                            continue
                        v, d, l = nums[i], nums[j], nums[k]
                        if v > d > 0 and abs(v - d - l) < (v * 0.05):  # 5% tolerance
                            return (v, d, l)

        return None

    @staticmethod
    def _parse_ocr_valor(s: str) -> float:
        """
        Converte string de valor OCR (sem formatação) para float.

        OCR omite separadores: '18583' → 18583.00 → R$18.583,00
        Assume que valores > 10000 têm 2 casas decimais implícitas.
        """
        try:
            v = float(s.replace(',', '.').replace('.', ''))
            # Se o número parece grande demais para ser em reais,
            # assume que os 2 últimos dígitos são centavos
            # Ex: 1858300 → 18583.00
            if v > 100000:
                v = v / 100
            return v
        except (ValueError, AttributeError):
            return 0.0

    # ------------------------------------------------------------------ #
    # Validação — mais leniente para texto OCR                            #
    # ------------------------------------------------------------------ #

    def _validate_holerite(self, holerite) -> bool:
        """
        Validação adaptada para OCR: aceita CPF vazio e lista de verbas vazia.

        O OCR de PDFs-imagem fragmenta dados numéricos como CPF de forma
        irrecuperável. Nome e verbas são extraídos com melhor qualidade.
        Não bloquear holerites por CPF — usar nome como identificador.
        """
        if not holerite.cabecalho:
            raise ValueError("Cabeçalho is required")
        if not holerite.cabecalho.nome:
            raise ValueError("Nome is required")
        # CPF e verbas vazias são aceitas para holerites OCR
        return True

    # ------------------------------------------------------------------ #
    # Extração de verbas — regex leniente para OCR                        #
    # ------------------------------------------------------------------ #

    # Mapeamento OCR: letras comumente confundidas com dígitos
    _OCR_CHAR_MAP = {
        'o': '0', 'O': '0',
        'z': '2', 'Z': '2',
        's': '5', 'S': '5',
        'l': '1', 'i': '1', 'I': '1',
        'g': '6', 'G': '6',
        'a': '4',
        'b': '6', 'q': '9',
        't': '1',
    }

    @classmethod
    def _fix_ocr_code(cls, raw: str) -> str:
        """
        Converte código OCR garbled para formato numérico XX.XXX.

        Substitui letras por dígitos equivalentes (confusões típicas de OCR)
        e normaliza para o formato padrão DDPE.
        """
        digits = ''.join(cls._OCR_CHAR_MAP.get(c, c) for c in raw if c != '.')
        # Descarta se ainda houver letras após substituição
        if not re.match(r'^\d{4,6}$', digits):
            return ""
        if len(digits) >= 5:
            return f"{digits[:2]}.{digits[2:5]}"
        return digits

    def _extract_verbas(self):
        """
        Extração de verbas tolerante a ruído OCR.

        Usa regex mais permissivo que aceita tokens alfanuméricos como
        código de verba (depois converte para dígitos via _fix_ocr_code).
        Mantém a lógica de valor e denominação do parser pai.
        """
        import re as _re
        from src.core.normalizer import CodigoVerbaNormalizer
        from src.core.data_model import Verba, NaturezaVerba

        if not self.paginas:
            return []

        verbas = []

        # Regex leniente: código pode ter letras de OCR (mínimo 3 chars, máximo 7)
        codigo_start = _re.compile(r'^([0-9A-Za-z]{2,3}[.\s]?[0-9A-Za-z]{3})\s+')
        valor_end_full = _re.compile(r'([-]?\d[\d.,]*\d)\s*([+\-])\s*$')
        valor_end_simple = _re.compile(r'([-]?\d[\d.,]*\d)\s*$')
        standalone_valor_re = _re.compile(r'^([-]?\d[\d.,]*\d)\s*([+\-])\s*$')

        for page in self.paginas:
            lines = page.texto.split('\n')
            pending_valor = None

            for line in lines:
                line_upper = line.upper()
                line_stripped = line.strip()

                if 'TOTAL' in line_upper or 'LÍQUIDO' in line_upper or 'LIQUIDO' in line_upper:
                    break
                if not line_stripped or 'CÓDIGO' in line_upper or 'CÓDIGO' in line_upper:
                    pending_valor = None
                    continue

                codigo_match = codigo_start.match(line_stripped)
                if not codigo_match:
                    sv_match = standalone_valor_re.match(line_stripped)
                    if sv_match:
                        pending_valor = (sv_match.group(1), sv_match.group(2))
                    else:
                        pending_valor = None
                    continue

                try:
                    codigo_raw = codigo_match.group(1)
                    # Normalizar código OCR
                    codigo_fixado = self._fix_ocr_code(codigo_raw)
                    if not codigo_fixado:
                        pending_valor = None
                        continue

                    rest = line_stripped[codigo_match.end():]

                    # Tentar extrair valor — mesma lógica do pai
                    valor_match = valor_end_full.search(rest)
                    if valor_match:
                        valor_str = valor_match.group(1)
                        sinal = valor_match.group(2)
                        valor = self._parse_valor(valor_str)
                        valor = -abs(valor) if sinal == '-' else abs(valor)
                        middle = rest[:valor_match.start()].strip()
                        pending_valor = None
                    elif pending_valor:
                        valor_str, sinal = pending_valor
                        valor = self._parse_valor(valor_str)
                        valor = -abs(valor) if sinal == '-' else abs(valor)
                        middle = rest.strip()
                        pending_valor = None
                    else:
                        valor_match = valor_end_simple.search(rest)
                        if not valor_match:
                            continue
                        valor_str = valor_match.group(1)
                        valor = self._parse_valor(valor_str)
                        middle = rest[:valor_match.start()].strip()

                    if valor == 0.0:
                        continue

                    # Extrair denominação (tudo antes do NAT/unidade)
                    denominacao = _re.sub(
                        r'\s+[NARDE]\s.*$|\s+(?:VALOR|PERC\.|DIAS|AULAS|HORAS|QTDE).*$',
                        '', middle, flags=_re.IGNORECASE
                    ).strip() or middle.split()[0] if middle else "OCR"

                    codigo = CodigoVerbaNormalizer.normalize(codigo_fixado)

                    verba = Verba(
                        codigo=codigo,
                        denominacao=denominacao or "UNKNOWN",
                        natureza=NaturezaVerba.NORMAL,
                        valor=valor,
                        qualificadores_detectados=[],
                    )
                    verbas.append(verba)

                except (ValueError, AttributeError, IndexError):
                    continue

        return verbas

    # ------------------------------------------------------------------ #
    # Limpeza de texto OCR                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _clean_ocr(texto: str) -> str:
        """
        Remove ruídos típicos de OCR em holerites capturados de app mobile.

        Transformações aplicadas:
        - Remove linhas de UI (hora do celular, botões de navegação)
        - Remove bordas de tabela OCR'd como '|'
        - Corrige 'o' confundido com '0' no início de códigos de verba
        - Normaliza espaços excessivos
        """
        linhas_limpas = []
        for linha in texto.split("\n"):
            # Descartar linhas de UI do app mobile
            if any(
                re.search(p, linha, re.IGNORECASE)
                for p in DDPEAtivoImagemParser._UI_NOISE_PATTERNS
            ):
                continue

            # Remover pipes de bordas de tabela
            linha = re.sub(r"\s*\|\s*", " ", linha)

            # Corrigir 'o' inicial confundido com '0' antes de dígitos de código
            # Ex: "o1038" → "01038",  "o91.036" → "091.036"
            linha = re.sub(r"^o(\d)", r"0\1", linha.strip())

            # Normalizar espaços múltiplos
            linha = re.sub(r" {2,}", " ", linha).strip()

            if linha:
                linhas_limpas.append(linha)

        return "\n".join(linhas_limpas)
