"""CLI entry point for HoleritePRO"""

import sys
from pathlib import Path

# Quick test of basic functionality
if __name__ == "__main__":
    from src.core import (
        Holerite,
        CabecalhoHolerite,
        Verba,
        NaturezaVerba,
        TemplateType,
        CodigoVerbaNotmalizer,
        AlocacaoTemporal,
    )

    print("[OK] HoleritePRO v0.1.0 - Core Engine")
    print()

    # Test 1: Create a holerite
    print("[TEST 1] Creating holerite...")
    cab = CabecalhoHolerite(
        nome="LUCIANO BASTOS DE SOUZA",
        cpf="123.456.789-00",
        competencia="2021-03",
        template_type=TemplateType.DDPE,
    )

    hol = Holerite(cabecalho=cab)
    hol.add_verba(
        Verba(
            codigo="70.006",
            denominacao="IAMSPE",
            natureza=NaturezaVerba.NORMAL,
            valor=1000.0,
        )
    )
    hol.add_verba(
        Verba(
            codigo="70.007",
            denominacao="IAMSPE ADICIONAL",
            natureza=NaturezaVerba.NORMAL,
            valor=500.0,
        )
    )
    hol.calcula_totais()
    print(f"  Nome: {hol.cabecalho.nome}")
    print(f"  CPF: {hol.cabecalho.cpf}")
    print(f"  Competencia: {hol.cabecalho.competencia}")
    print(f"  Verbas: {len(hol.verbas)}")
    print(f"  Total Vencimentos: R$ {hol.total_vencimentos:.2f}")
    print(f"  Total Descontos: R$ {hol.total_descontos:.2f}")
    print(f"  Liquido: R$ {hol.liquido:.2f}")
    print()

    # Test 2: Normalize codes
    print("[TEST 2] Code normalization...")
    codigo_ddpe = "70.006"
    codigo_norm = CodigoVerbaNotmalizer.normalize(codigo_ddpe)
    codigo_display = CodigoVerbaNotmalizer.to_display_format(codigo_norm)
    print(f"  {codigo_ddpe} -> {codigo_norm} -> {codigo_display}")
    print()

    # Test 3: Temporal allocation
    print("[TEST 3] Temporal allocation...")
    mes_alocacao = AlocacaoTemporal.get_mes_alocacao("2021-03", "A")
    print(f"  Atrasado de MAR/2021 -> {mes_alocacao}")

    inicio, fim = AlocacaoTemporal.get_periodo_padrao(5)
    print(f"  Periodo padrao (5 anos): {inicio} a {fim}")
    print()

    print("[SUCCESS] Core Engine Setup Complete!")
    print("  Ready for PDF reader and parsers...")
