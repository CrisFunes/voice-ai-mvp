import pandas as pd
from database import get_db_session
from models import Client, Accountant

df = pd.read_csv('DATABASE_CLIENTI-PROFESSIONISTI_-_Clienti.csv')

with get_db_session() as db:
    for idx, row in df.iterrows():
        client = Client(
            company_name=row['Ragione Sociale'],
            tax_code=row['Codice Fiscale / P.IVA'],
            phone=row['Telefono'],
            email=row['Email'],
            address=row['Indirizzo'],
            accountant_id=find_accountant_by_name(row['Commercialista'])
        )
        db.add(client)
    
    db.commit()
