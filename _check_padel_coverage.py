"""Verifie si le padel est sous-compte dans Data ES."""
import requests
from collections import Counter

B = "https://data.sports.gouv.fr/api/explore/v2.1/catalog/datasets/equipements-sportifs/records"

def count(where):
    r = requests.get(B, params={"where": where, "limit": 1}, timeout=60)
    r.raise_for_status()
    return r.json()["total_count"]

checks = {
    "type = Piste de padel": 'equip_type_name = "Piste de padel"',
    "type like %padel%": 'equip_type_name like "%padel%"',
    "type like %paddle%": 'equip_type_name like "%paddle%"',
    "nom like %padel%": 'equip_nom like "%padel%"',
    "nom like %paddle%": 'equip_nom like "%paddle%"',
    "aps like %padel%": 'aps_name like "%padel%"',
    "aps like %paddle%": 'aps_name like "%paddle%"',
    "obs like %padel%": 'equip_obs like "%padel%"',
    "padel OR paddle (large)": (
        'equip_type_name like "%padel%" OR equip_type_name like "%paddle%" OR '
        'equip_nom like "%padel%" OR equip_nom like "%paddle%" OR '
        'aps_name like "%padel%" OR aps_name like "%paddle%" OR '
        'inst_nom like "%padel%" OR inst_nom like "%paddle%"'
    ),
}

print("=== COMPTAGES ===")
for label, where in checks.items():
    try:
        n = count(where)
        print(f"{n:7d}  {label}")
    except Exception as e:
        print(f"ERR     {label}: {e}")

# Types des fiches dont le NOM contient padel mais pas type piste
print("\n=== Types quand equip_nom contient padel ===")
r = requests.get(
    B,
    params={
        "where": 'equip_nom like "%padel%" OR equip_nom like "%paddle%"',
        "select": "equip_type_name,count(*) as n",
        "group_by": "equip_type_name",
        "order_by": "n desc",
        "limit": 30,
    },
    timeout=60,
)
r.raise_for_status()
for rec in r.json()["results"]:
    print(f"  {rec['n']:5d}  {rec['equip_type_name']}")

print("\n=== Activites (aps_name) contenant padel — echantillon types ===")
r = requests.get(
    B,
    params={
        "where": 'aps_name like "%padel%" OR aps_name like "%paddle%"',
        "select": "equip_type_name,count(*) as n",
        "group_by": "equip_type_name",
        "order_by": "n desc",
        "limit": 30,
    },
    timeout=60,
)
r.raise_for_status()
for rec in r.json()["results"]:
    print(f"  {rec['n']:5d}  {rec['equip_type_name']}")

# periodes de mise en service padel
print("\n=== Periodes mise en service — Piste de padel ===")
r = requests.get(
    B,
    params={
        "where": 'equip_type_name = "Piste de padel"',
        "select": "equip_service_periode,count(*) as n",
        "group_by": "equip_service_periode",
        "order_by": "n desc",
        "limit": 20,
    },
    timeout=60,
)
for rec in r.json().get("results", []):
    print(f"  {rec['n']:5d}  {rec.get('equip_service_periode')}")
