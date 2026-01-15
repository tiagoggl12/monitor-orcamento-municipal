import sys
sys.path.insert(0, '/app')

from app.database import SessionLocal  
from app.models.dashboard_models import ExercicioOrcamentario, InvestimentoRegional
from sqlalchemy import desc

db = SessionLocal()

# Buscar LOA 2026
exercicios = db.query(ExercicioOrcamentario).filter(
    ExercicioOrcamentario.ano == 2026
).all()

print(f"Total de exercícios 2026: {len(exercicios)}")

for ex in exercicios:
    print(f"\nExercício: {ex.ano} - {ex.municipio} - {ex.tipo_documento}")
    print(f"  ID: {ex.id}")
    print(f"  Status: {ex.status}")
    print(f"  Orçamento: R$ {ex.orcamento_total:,.2f}")
    
    regionais = db.query(InvestimentoRegional).filter(
        InvestimentoRegional.exercicio_id == ex.id
    ).limit(5).all()
    
    print(f"  Regionais (primeiras 5):")
    for reg in regionais:
        print(f"    - Regional {reg.regional_numero}: R$ {reg.valor_total:,.2f}")

db.close()
