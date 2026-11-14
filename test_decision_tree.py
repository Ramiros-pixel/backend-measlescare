
from app.expert_system.decision_tree import run_decision_tree


fakta_pasien = {
    "DEMAM": 1,
    "RUAM": 1,
    "RUAM_MENYELURUH": 1,
    "BATUK": 1,
    "PILEK": 0,
    "MATA_MERAH": 0,
    "SESAK": 0,
    "KEJANG": 0,
    "PENURUNAN_KESADARAN": 0,
}


hasil = run_decision_tree(fakta_pasien)


print("\nHASIL DECISION TREE")

print("Metode:", hasil["metode"])

print("\nMAIN DECISION TREE")

print("Leaf:", hasil["main_leaf"])

print("Kesimpulan:", hasil["summary"]["main"])

print("\nJalur keputusan:")

for node in hasil["decision_path"]["main"]:
    print(
        f'{node["node"]} '
        f'({node["pertanyaan"]}) '
        f'-- {node["jawaban"]} --> '
        f'{node["next"]}'
    )


print("\nSAFETY DECISION TREE")

print("Leaf:", hasil["safety_leaf"])

print("Kesimpulan:", hasil["summary"]["safety"])

print("\nJalur keputusan:")

for node in hasil["decision_path"]["safety"]:
    print(
        f'{node["node"]} '
        f'({node["pertanyaan"]}) '
        f'-- {node["jawaban"]} --> '
        f'{node["next"]}'
    )


print("\nSAFETY ALERT:", hasil["safety_alert"])
