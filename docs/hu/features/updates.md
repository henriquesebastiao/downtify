---
icon: lucide/download
---

# Frissítési értesítések

A Downtify óránként egyszer ellenőrzi a saját [GitHub Releases oldalát](https://github.com/henriquesebastiao/downtify/releases). Ha újabb verzió jelent meg, minden oldalon értesítés jelenik meg az oldalsáv alján — telefonon egy pont a **Továbbiak** fülön és egy sor a lapja tetején —, valamint a **Beállítások → Névjegy** oldalon:

> ✦ 3.0.1 frissítés elérhető

Kattints rá, hogy megnyisd a kiadást a GitHubon.

## Hogyan működik

- A backend egy háttérfeladata (`downtify/update_check.py`) induláskor azonnal egyszer, majd óránként lekéri a legújabb kiadást a GitHub API-jából. „Elindítom és elfelejtem” jellegű: a felületen semmi sem vár rá.
- A webes felület óránként egyszer olvassa a gyorsítótárazott eredményt a `GET /api/check_update` végpontról (lásd: [API-referencia](../api-reference.md)), és megjeleníti az értesítést, ha újabb verziót talál.
- A verziókat számszerűen hasonlítja össze (a `2.10.0` < `2.9.0` hamis, ellentétben az egyszerű szövegösszehasonlítással), a kiadási címke elején álló opcionális `v` előtagot pedig figyelmen kívül hagyja.

## Ha a GitHub nem érhető el

A sikertelen ellenőrzést (offline gazdagép, GitHub-korlát) naplózza, és a következő óránkénti körben egyszerűen újrapróbálja — az előző eredmény, ha van, addig érvényben marad. Az ellenőrzés soha nem akadályoz semmi mást, amit a Downtify csinál; nincs róla felhasználónak szóló hibaüzenet.

## Semmi sem töltődik le automatikusan

Ez csak *szól*, hogy létezik új verzió — a Downtify nem frissíti magát. A tényleges frissítéshez húzd le az új képet, és hozd létre újra a konténert:

```bash
docker compose pull
docker compose up -d
```
