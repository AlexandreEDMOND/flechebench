import unittest
from datetime import date

from flechebench.data.leparisien import GRID_URL, enrich_grid, latest_issues, parse_menu, parse_mfj


MFJ_SAMPLE = """var gamedata = {
titre:"mfleches_1_4011",
legende:"",
force:"1",
nbcaseslargeur:14,
nbcaseshauteur:9,
grille:[
"vBcNkPnDcTlScZ",
"TONIFIERhESOPE",
"dChELEPHANTSbS",
"SKATEbRaBUEhET",
"dbPgUNIRAfPORE",
"PILORIShTAPIRb",
"rNATOfENTRESOL",
"PONANTaERaSONO",
"aXIIaANTESaNEF"],
definitions:[
["POT À","BIÈRE"],
["FORTIFIER"],
["REFUS","RUSSE"],
["OISEAU","BAVARD"],
["ORNE–","MENT","FLORAL"],
["CHARGÉ","DE","RECRU–","TEMENT"],
["ENTICHÉE"],
["TEL LE","PARI DE","CELUI QUI","A TOPÉ"],
["À L'AIDE !"],
["GRANDES","PLAINES"],
["UN PEU","DE PEAU","D'ORANGE"],
["SOURCE","DE LA","FONTAINE"],
["DÉMOLIR","UN MUR"],
["PLANCHE","À ROU–","LETTES"],
["MAMMIFÈ–","RES À","TROMPE"],
["NIVELÉ,","ÉGALISÉ"],
["QUI EST","DONC À","CORRIGER"],
["NÉGATION","QUI VA","PAR DEUX"],
["CONSOM–","MÉE AU","BAR"],
["POUR","AJOUTER","UN MOT"],
["PETIT DE","L'OIE"],
["POTEAUX","DES CON–","DAMNÉS"],
["ACIER","POUR","DES COU–","VERTS"],
["ASSEM–","BLERA"],
["ENLEVAI"],
["ORIFICE","CUTANÉ"],
["COURT","ALLER-","RETOUR"],
["SE","CACHER","(SE)"],
["IMPEC–","CABLE"],
["CÔTÉ AU","VENT"],
["L'OTAN","À WA–","SHINGTON"],
["OCCIDENT"],
["DEMI-","ÉTAGE"],
["DEVANT","CE QUI","EST À TOI"],
["FIN DE","VERBE DU","PREMIER","GROUPE"],
["ÉQUIPE–","MENT","POUR LE","BAL","PUBLIC"],
["DOUZE","ROMAIN"],
["PILIERS","DE COINS"],
["PARTIE","DE CA–","THÉDRALE","OU VIEUX","NAVIRE"]
],
spountzV:[],
spountzH:[[8,2],[8,1],[12,2],[12,1],[10,6]],
photos:[],
concours:[],
enonceconcours:""
};"""


class LeParisienTests(unittest.TestCase):
    def test_parse_menu(self) -> None:
        menu = 'var tousjeux = {"040726": ["4010","1",""], "050726": ["4011","1",""]};'

        issues = parse_menu(menu, 1)

        self.assertEqual([issue.number for issue in issues], ["4010", "4011"])
        self.assertEqual([issue.force for issue in issues], [1, 1])
        self.assertEqual(issues[-1].published_on.isoformat(), "2026-07-05")

    def test_parse_menu_uses_requested_force_not_menu_flag(self) -> None:
        menu = 'var tousjeux = {"050726": ["1519","1",""]};'

        issues = parse_menu(menu, 3)

        self.assertEqual(issues[0].number, "1519")
        self.assertEqual(issues[0].force, 3)

    def test_grid_url_uses_shared_grid_directory(self) -> None:
        self.assertEqual(
            GRID_URL.format(force=3, number="1519"),
            "https://static.rcijeux.fr/drupal_game/leparisien/mfleches1/grids/mfleches_3_1519.mfj",
        )

    def test_latest_issues_filters_future_dates(self) -> None:
        def fake_fetch(_url: str) -> str:
            return (
                'var tousjeux = {'
                '"040726": ["4010","1",""], '
                '"050726": ["4011","1",""], '
                '"061226": ["4165","1",""]'
                "};"
            )

        import flechebench.data.leparisien as leparisien

        original_fetch = leparisien.fetch_text
        leparisien.fetch_text = fake_fetch
        try:
            issues = latest_issues(1, 10, through_date=date(2026, 7, 5))
        finally:
            leparisien.fetch_text = original_fetch

        self.assertEqual([issue.number for issue in issues], ["4010", "4011"])

    def test_enrich_grid_entries(self) -> None:
        gamedata = parse_mfj(MFJ_SAMPLE)

        puzzle = enrich_grid(gamedata, force=1, number="4011", published_on=None)

        self.assertEqual(puzzle["width"], 14)
        self.assertEqual(len(puzzle["entries"]), 39)
        self.assertEqual(puzzle["entries"][0]["clue"], "POT À BIÈRE")
        self.assertEqual(puzzle["entries"][0]["answer"], "BOCK")
        self.assertEqual(puzzle["entries"][-1]["clue"], "PARTIE DE CATHÉDRALE OU VIEUX NAVIRE")
        self.assertEqual(puzzle["entries"][-1]["answer"], "NEF")


if __name__ == "__main__":
    unittest.main()
