import unittest
import os
from services import processar_cadastro, processar_consumo
from database import init_db, get_session, Cadastro, ConsumoResumido

class TestValidacao(unittest.TestCase):

    def setUp(self):
        init_db()

    def test_cadastro(self):
        qtd = processar_cadastro("uploads/cadastro.csv")
        self.assertGreater(qtd, 0)

        session = get_session()
        count = session.query(Cadastro).count()
        session.close()

        self.assertEqual(count, qtd)

    def test_consumo(self):
        qtd = processar_consumo("uploads/consumo.csv")
        self.assertGreater(qtd, 0)

        session = get_session()
        count = session.query(ConsumoResumido).count()
        session.close()

        self.assertEqual(count, qtd)

if __name__ == "__main__":
    unittest.main()