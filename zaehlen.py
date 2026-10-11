#!/usr/bin/env python3
"""Zählt Maxis echte Commits pro Tag (letzte 84 Tage) über die Projekt-Repos auf diesem Mac.
Schreibt nur Zahlen nach aktivitaet.json (keine Repo-Namen, keine Commit-Texte) und pusht, wenn sich etwas geändert hat.
Läuft stündlich per launchd (de.maxi.bau-aktivitaet)."""
import json, subprocess, datetime, pathlib, os

HOME = pathlib.Path.home()
WURZELN = [HOME / "Developer", HOME]
# automatische Spiegel/Backups zählen nicht als Bauen
AUSSCHLUSS = {"claude-limits", "todoist-github", "mattea-tabelle", "notenapp-github", "depot-status", "ki-depot", "bau-aktivitaet",
              "whatsapp-spiegel", "mail-spiegel", "instagram-spiegel", "zoho-mail-spiegel"}
TAGE = 84

def repos():
    gefunden = set()
    for w in WURZELN:
        for git in list(w.glob("*/.git")) + list(w.glob("*/*/.git")):
            r = git.parent
            if r.name in AUSSCHLUSS or r.parent.name in AUSSCHLUSS or "Library" in r.parts:
                continue
            gefunden.add(r)
    return gefunden

def main():
    heute = datetime.date.today()
    start = heute - datetime.timedelta(days=TAGE - 1)
    commits = {}
    for r in repos():
        try:
            out = subprocess.run(["git", "-C", str(r), "log", "--all", f"--since={TAGE}.days", "--format=%H %ad", "--date=short"],
                                 capture_output=True, text=True, timeout=60).stdout
        except Exception:
            continue
        for zeile in out.splitlines():
            h, _, d = zeile.partition(" ")
            commits[h] = d  # gleiche Commits in Worktrees nur einmal
    tage = {(start + datetime.timedelta(days=i)).isoformat(): 0 for i in range(TAGE)}
    for d in commits.values():
        if d in tage:
            tage[d] += 1
    letzter = None
    for r in repos():
        try:
            t = subprocess.run(["git", "-C", str(r), "log", "--all", "-1", "--format=%cI"], capture_output=True, text=True, timeout=30).stdout.strip()
            if t and (letzter is None or t > letzter):
                letzter = t
        except Exception:
            pass
    daten = {"_hinweis": "Commits pro Tag aus Maxis Projekt-Repos (ohne automatische Spiegel). Nur Zahlen.",
             "tage": [{"d": d, "n": n} for d, n in tage.items()], "gesamt": sum(tage.values()), "letzterCommit": letzter}
    ziel = pathlib.Path(__file__).with_name("aktivitaet.json")
    neu = json.dumps(daten, ensure_ascii=False, indent=1) + "\n"
    if ziel.exists() and ziel.read_text() == neu:
        return
    ziel.write_text(neu)
    os.chdir(ziel.parent)
    subprocess.run(["git", "add", "aktivitaet.json"], check=True)
    subprocess.run(["git", "commit", "-q", "-m", f"Stand {datetime.datetime.now():%d.%m. %H:%M}"], check=True)
    subprocess.run(["git", "push", "-q", "origin", "main"], check=True)

if __name__ == "__main__":
    main()
