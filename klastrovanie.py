import copy
import random
import math
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt

FARBY = ['green', 'orange', 'brown', 'dodgerblue']
rozsah = 5000
pocet_prvotnych_bodov = 20
pocet_bodov = 20000


def inicializuj_body():
    pole = {

    }
    for i in range(0, pocet_prvotnych_bodov):
        x, y = random.randint(-rozsah, rozsah), random.randint(-rozsah, rozsah)

        if (x, y) in pole.values():
            i -= 1
            continue

        pole.update({i: (x, y)})

    print(pole)
    print("velkost pola ", len(pole))

    for i in range(0, pocet_bodov):
        x, y = pole.get(random.randint(0, pocet_prvotnych_bodov - 1))
        x += random.randint(-100, 100)
        y += random.randint(-100, 100)

        pole.update({i + 20: (x, y)})

    return pole


def zarad_do_klustru(suradnice, klustre):
    x, y = suradnice
    najblizsi_kluster = []
    najmensia_dlzka = 0

    for pole in klustre:
        x_k, y_k, tmp = pole[0]
        rozdiel_x = abs(x - x_k)
        rozdiel_y = abs(y - y_k)
        dlzka_cesty = math.sqrt(rozdiel_y ** 2 + rozdiel_x ** 2)
        if dlzka_cesty > najmensia_dlzka:
            x_k, y_k, farba = pole[0]
            najmensia_dlzka  = dlzka_cesty
            najblizsi_kluster = pole

    najblizsi_kluster.append((x, y, farba))


def vypocitaj_centroidy(klustre):
    for pole in klustre:
        sum_x = 0
        sum_y = 0
        counter = 0
        # farba = pole[0][2]
        for suradnice in pole:
            x, y, farba = suradnice
            if counter > 0:
                sum_x += x
                sum_y += y

            counter += 1

        pole[0] = (int(sum_x/counter), int(sum_y/counter), farba)


def reset_klustrov(klustre):
    for i in range(0, len(klustre)):
        klustre[i] = [klustre[i][0]]

    return klustre


def k_means_centroid_klustruj(pole, klustre):
    klustre = reset_klustrov(klustre)

    for i in range(0, pocet_bodov + pocet_prvotnych_bodov):
        zarad_do_klustru(pole.get(i), klustre)

    vypocitaj_centroidy(klustre)


def skontroluj(pole1, pole2):
    for i in range(0, len(pole1)):
        koniec = 1
        for k in range(0, len(pole2)):
            if pole1[i][0:1] == pole2[k][0:1]:
                koniec = 0
                break
        if koniec == 1:
            return False
    return True


def vyrob_graf(klustre):
    for i in range(0, len(klustre)):
        print(klustre[i][0])
        klustre[i][0] = (klustre[i][0][0], klustre[i][0][1], FARBY[-(i + 1)])
        print(klustre[i][0])
        print(FARBY[-i])
        if i == 0:
            df = pd.DataFrame(klustre[i], columns=["x", "y", "color"])
        else:
            df = df.append(pd.DataFrame(klustre[i], columns=["x", "y", "color"]), ignore_index=True)

    sns.scatterplot(data=df, x="x", y="y", hue="color", palette=FARBY, legend= 'full')
    plt.show()


def k_means_centroid(pole):
    klustre = []
    nove_centroidy = []
    k = int(input("Zadaj počet klustrov: "))
    for i in range(0, k):
        x, y = (random.randint(-rozsah, rozsah), random.randint(-rozsah, rozsah))
        klustre.append([(x, y, FARBY[i])])
        print(f"centroid {i}:", klustre[i])
        nove_centroidy.insert(i, (x, y, FARBY[i]))

    while True:
        k_means_centroid_klustruj(pole, klustre)
        centroidy = nove_centroidy
        nove_centroidy = []

        counter = 0
        for kluster in klustre:
            nove_centroidy.insert(0, kluster[0])
            counter += 1

        if skontroluj(nove_centroidy, centroidy):
            break

    vyrob_graf(klustre)

p = inicializuj_body()
k_means_centroid(p)
