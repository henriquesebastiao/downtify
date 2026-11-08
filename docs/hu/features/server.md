---
icon: lucide/hard-drive
---

# Szerverbeállítások

A **Beállítások → Szerver** azt tartalmazza, hogyan fut maga a szerver. Csak az adminisztrátorok látják (lásd: [Felhasználók és bejelentkezés](users.md#admins-and-users)).

## A port módosítása

A Downtify a **8000**-es porton figyel. Az adminisztrátor a **Beállítások → Szerver → Port** alatt választhat másikat (1024–65535):

- A **Mentés** a szerver következő indításáig megőrzi.
- A **Mentés és újraindítás** azonnal újraindítja a szervert ezen a porton. A folyamatban lévő letöltések leállnak, az oldalak és az alkalmazások újracsatlakoznak. A szerver saját címén (pl. `http://nas:8000`) megnyitott oldal megvárja a szervert, és magától megnyitja az új címet; bejelentkezve maradsz.

Ha a port a `DOWNTIFY_PORT` (vagy `PORT`) környezeti változóból vagy a parancssori `--port` kapcsolóból származik — ezek mindig elsőbbséget élveznek —, a mező a használt portot mutatja, de nem szerkeszthető, és az oldal megmondja, melyik állítja be. Töröld (és indítsd újra), hogy a Beállításokban választhass portot.

::: warning A Docker bridge hálózata rögzített portot képez le
Az alapértelmezett Docker-telepítésben (`ports: - '8000:8000'`) a konténer portjának egyeznie kell a leképezéssel. A Beállításokban történt módosítás után állítsd át a leképezést az új portra (`'9000:9000'`), és hozd létre újra a konténert — vagy futtasd `network_mode: host` móddal. Különben a Downtify nem érhető el. A visszajutáshoz állítsd a `DOWNTIFY_PORT` értékét a régi portra: elsőbbséget élvez a Beállításokkal szemben.
:::

[Fordított proxy](mobile-apps.md#behind-a-reverse-proxy) mögött a proxyt is az új portra kell irányítani. A [párosított alkalmazások](mobile-apps.md) azt a címet használják, amelyet kaptak: a port módosítása után add meg az újat az alkalmazásban.
