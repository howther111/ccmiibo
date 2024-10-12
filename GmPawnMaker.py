#!/usr/bin/env python
# -*- coding: utf8 -*-
import sys
import tkinter
import tkinter.messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json


class GuardianData():
    character_name = ""
    #guardian_name = ""
    level = 0
    #guardian_size = ""
    player_name = ""
    strong_total = 0
    strong_bonus = 0
    reflex_total = 0
    reflex_bonus = 0
    sense_total = 0
    sense_bonus = 0
    intellect_total = 0
    intellect_bonus = 0
    will_total = 0
    will_bonus = 0
    bllesing_total = 0
    bllesing_bonus = 0
    specials_000 = ""
    specials_001 = ""
    specials_002 = ""
    specials_003 = ""
    specials_004 = ""
    add_fortune_point = 0
    outfits_total_hit = 0
    outfits_total_dodge = 0
    outfits_total_magic = 0
    outfits_total_countermagic = 0
    outfits_total_action = 0
    outfits_total_hp = 0
    outfits_total_mp = 0
    outfits_total_attack = 0
    outfits_total_battlespeed_total = ""

    outfits_rightname = ""
    outfits_rightattack = ""
    outfits_rightrange = ""
    outfits_rightstrong = ""

    outfits_leftname = ""
    outfits_leftattack = ""
    outfits_leftrange = ""
    outfits_leftstrong = ""

    outfits_magicrightname = ""
    outfits_magicrightattack = ""
    outfits_magicrightrange = ""
    outfits_magicrightstrong = ""

    outfits_magicleftname = ""
    outfits_magicleftattack = ""
    outfits_magicleftrange = ""
    outfits_magicleftstrong = ""

    armourstotal_slash = 0
    armourstotal_pierce = 0
    armourstotal_crash = 0
    armourstotal_fire = 0
    armourstotal_ice = 0
    armourstotal_thunder = 0
    armourstotal_light = 0
    armourstotal_dark = 0

    items = []

    break_flg = 0

    url = ""

    def input_data(self, driver, input_url):
        self.url = input_url
        self.character_name = driver.find_element(by=By.ID, value="base.name").get_attribute("value")
        #self.guardian_name = driver.find_element(by=By.ID, value="base.guardian.name").get_attribute("value")
        self.level = driver.find_element(by=By.ID, value="base.level").get_attribute("value")
        #self.guardian_size = driver.find_element(by=By.ID, value="base.guardian.size").get_attribute("value")
        self.player_name = driver.find_element(by=By.ID, value="base.player").get_attribute("value")
        self.strong_total = driver.find_element(by=By.ID, value="abl.strong.total").get_attribute("value")
        self.strong_bonus = driver.find_element(by=By.ID, value="abl.strong.bonus").get_attribute("value")
        self.reflex_total = driver.find_element(by=By.ID, value="abl.reflex.total").get_attribute("value")
        self.reflex_bonus = driver.find_element(by=By.ID, value="abl.reflex.bonus").get_attribute("value")
        self.sense_total = driver.find_element(by=By.ID, value="abl.sense.total").get_attribute("value")
        self.sense_bonus = driver.find_element(by=By.ID, value="abl.sense.bonus").get_attribute("value")
        self.intellect_total = driver.find_element(by=By.ID, value="abl.intellect.total").get_attribute("value")
        self.intellect_bonus = driver.find_element(by=By.ID, value="abl.intellect.bonus").get_attribute("value")
        self.will_total = driver.find_element(by=By.ID, value="abl.will.total").get_attribute("value")
        self.will_bonus = driver.find_element(by=By.ID, value="abl.will.bonus").get_attribute("value")
        self.bllesing_total = driver.find_element(by=By.ID, value="abl.bllesing.total").get_attribute("value")
        self.bllesing_bonus = driver.find_element(by=By.ID, value="abl.bllesing.bonus").get_attribute("value")
        self.specials_000 = driver.find_element(by=By.ID, value="specials.0.name").get_attribute("value")
        self.specials_001 = driver.find_element(by=By.ID, value="specials.001.name").get_attribute("value")
        self.specials_002 = driver.find_element(by=By.ID, value="specials.002.name").get_attribute("value")
        try:
            self.specials_003 = driver.find_element(by=By.ID, value="specials.003.name").get_attribute("value")

        except:
            pass

        try:
            self.specials_004 = driver.find_element(by=By.ID, value="specials.004.name").get_attribute("value")

        except:
            pass

        self.outfits_total_hit = driver.find_element(by=By.ID, value="outfits.total.hit").get_attribute("value")
        self.outfits_total_dodge = driver.find_element(by=By.ID, value="outfits.total.dodge").get_attribute("value")
        self.outfits_total_magic = driver.find_element(by=By.ID, value="outfits.total.magic").get_attribute("value")
        self.outfits_total_countermagic = driver.find_element(by=By.ID, value="outfits.total.countermagic").get_attribute("value")
        self.outfits_total_action = driver.find_element(by=By.ID, value="outfits.total.action").get_attribute("value")
        self.outfits_total_hp = driver.find_element(by=By.ID, value="outfits.total.hp").get_attribute("value")
        self.outfits_total_mp = driver.find_element(by=By.ID, value="outfits.total.mp").get_attribute("value")
        self.outfits_total_action = driver.find_element(by=By.ID, value="outfits.total.action").get_attribute("value")
        self.outfits_total_battlespeed_total = driver.find_element(by=By.ID, value="outfits.total.battlespeed.total").get_attribute("value")
        self.outfits_total_battlespeed_total = self.outfits_total_battlespeed_total.replace("ﾏｽ", "")

        self.add_fortune_point = driver.find_element(by=By.ID, value="fortunepoint").get_attribute("value")

        self.outfits_rightname = driver.find_element(by=By.ID, value="outfits.total.rightname").get_attribute("value")
        self.outfits_rightattack = driver.find_element(by=By.ID, value="outfits.total.rightattack").get_attribute("value")
        self.outfits_rightrange = driver.find_element(by=By.ID, value="outfits.total.rightrange").get_attribute("value")
        self.outfits_rightstrong = driver.find_element(by=By.ID, value="outfits.right.0.cost").get_attribute("value")

        self.outfits_leftname = driver.find_element(by=By.ID, value="outfits.total.leftname").get_attribute("value")
        self.outfits_leftattack = driver.find_element(by=By.ID, value="outfits.total.leftattack").get_attribute("value")
        self.outfits_leftrange = driver.find_element(by=By.ID, value="outfits.total.leftrange").get_attribute("value")
        self.outfits_leftstrong = driver.find_element(by=By.ID, value="outfits.left.0.cost").get_attribute("value")

        self.outfits_magicrightname = driver.find_element(by=By.ID,
                                                                value="outfits.total.magicrightname").get_attribute(
            "value")
        self.outfits_magicrightattack = driver.find_element(by=By.ID,
                                                                  value="outfits.total.magicrightattack").get_attribute(
            "value")
        self.outfits_magicrightrange = driver.find_element(by=By.ID,
                                                                 value="outfits.total.magicrightrange").get_attribute(
            "value")
        self.outfits_magicrightstrong = driver.find_element(by=By.ID,
                                                                  value="outfits.magicright.0.cost").get_attribute(
            "value")

        self.outfits_magicleftname = driver.find_element(by=By.ID,
                                                               value="outfits.total.magicleftname").get_attribute(
            "value")
        self.outfits_magicleftattack = driver.find_element(by=By.ID,
                                                                 value="outfits.total.magicleftattack").get_attribute(
            "value")
        self.outfits_magicleftrange = driver.find_element(by=By.ID,
                                                                value="outfits.total.magicleftrange").get_attribute(
            "value")
        self.outfits_magicleftstrong = driver.find_element(by=By.ID,
                                                                 value="outfits.magicleft.0.cost").get_attribute(
            "value")

        self.armourstotal_slash = driver.find_element(by=By.ID, value="armourstotal.slash").get_attribute("value")
        self.armourstotal_pierce = driver.find_element(by=By.ID, value="armourstotal.pierce").get_attribute("value")
        self.armourstotal_crash = driver.find_element(by=By.ID, value="armourstotal.crash").get_attribute("value")
        self.armourstotal_fire = driver.find_element(by=By.ID, value="armourstotal.fire").get_attribute("value")
        self.armourstotal_ice = driver.find_element(by=By.ID, value="armourstotal.ice").get_attribute("value")
        self.armourstotal_thunder = driver.find_element(by=By.ID, value="armourstotal.thunder").get_attribute("value")
        self.armourstotal_light = driver.find_element(by=By.ID, value="armourstotal.light").get_attribute("value")
        self.armourstotal_dark = driver.find_element(by=By.ID, value="armourstotal.dark").get_attribute("value")

        self.items.append(driver.find_element(by=By.ID, value="items.0.name").get_attribute("value"))

        for i in range(98):
            try:
                itemnum = i + 1
                itemstr = "items." + str(itemnum).zfill(3) + ".name"
                self.items.append(driver.find_element(by=By.ID, value=itemstr).get_attribute("value"))
            except:
                pass

        print(self.character_name)

    def output_text(self):
        # 駒のテキストデータを出力する
        text = "PC:" + self.character_name +  \
                   " PL:" + self.player_name + "\n" + \
                   "レベル:" + self.level

        text = text + "\n財産ポイント:" + self.add_fortune_point

        text = text + "\n【命中】" + str(self.outfits_total_hit) + \
                   "【回避】" + str(self.outfits_total_dodge) + \
                   "【魔導】" + str(self.outfits_total_magic) + \
                   "【抗魔】" + str(self.outfits_total_countermagic) + \
                   "【行動】" + str(self.outfits_total_action) + \
                   "\n【耐久】" + str(self.outfits_total_hp) + \
                   "【精神】" + str(self.outfits_total_mp) + \
                   "【移動力】" + str(self.outfits_total_battlespeed_total)

        text = text + "\n加護:" + self.specials_000 + "/" + self.specials_001 + "/" + self.specials_002

        if self.specials_003 != "":
            text = text + "/" + self.specials_003

        if self.specials_004 != "":
            text = text + "/" + self.specials_004

        text = text + "\n[*]武右:" + self.outfits_rightname + \
                " 射程:" + self.outfits_rightrange + \
                " 代償:" + self.outfits_rightstrong + \
                "\n攻撃力:" + self.outfits_rightattack

        text = text + "\n[*]武左:" + self.outfits_leftname + \
                " 射程:" + self.outfits_leftrange + \
                " 代償:" + self.outfits_leftstrong + \
                "\n攻撃力:" + self.outfits_leftattack

        text = text + "\n[*]魔右:" + self.outfits_magicrightname + \
                   " 射程:" + self.outfits_magicrightrange + \
                   " 代償:" + self.outfits_magicrightstrong + \
                   "\n攻撃力:" + self.outfits_magicrightattack

        text = text + "\n[*]魔左:" + self.outfits_magicleftname + \
                   " 射程:" + self.outfits_magicleftrange + \
                   " 代償:" + self.outfits_magicleftstrong + \
                   "\n攻撃力:" + self.outfits_magicleftattack

        text = text + "\n防御力:斬" + self.armourstotal_slash + \
                "/刺" + self.armourstotal_pierce + \
                "/殴" + self.armourstotal_crash + \
                "/炎" + self.armourstotal_fire + \
                "/氷" + self.armourstotal_ice + \
                "/雷" + self.armourstotal_thunder + \
                "/光" + self.armourstotal_light + \
                "/闇" + self.armourstotal_dark

        text = text + "\nアイテム:"
        for item in self.items:
            text = text + item + "/"
        text = text[:-1]

        print(text)

        file_name = self.character_name + "_キャラクターテキストデータ.txt"

        f = open(file_name, 'w', encoding="utf-8")
        f.write(text)
        f.close()

        print("キャラクターテキストデータを生成しました")
        self.output_porn(text)

    def output_porn(self, text_data):
        # 駒のココフォリア用データを出力する
        jsontext = {}
        jsontext["kind"] = "character"
        jsontext["data"] = {}
        jsontext["data"]["name"] = self.character_name
        jsontext["data"]["memo"] = text_data
        jsontext["data"]["initiative"] = int(self.outfits_total_action)
        jsontext["data"]["status"] = []

        jsontext["data"]["status"].append({})
        jsontext["data"]["status"][0]["label"] = "レベル"
        jsontext["data"]["status"][0]["value"] = self.level
        jsontext["data"]["status"][0]["max"] = self.level

        jsontext["data"]["status"].append({})
        jsontext["data"]["status"][1]["label"] = "HP"
        jsontext["data"]["status"][1]["value"] = self.outfits_total_hp
        jsontext["data"]["status"][1]["max"] = self.outfits_total_hp

        jsontext["data"]["status"].append({})
        jsontext["data"]["status"][2]["label"] = "MP"
        jsontext["data"]["status"][2]["value"] = self.outfits_total_mp
        jsontext["data"]["status"][2]["max"] = self.outfits_total_mp

        jsontext["data"]["status"].append({})
        jsontext["data"]["status"][3]["label"] = "財産ポイント"
        jsontext["data"]["status"][3]["value"] = self.add_fortune_point
        jsontext["data"]["status"][3]["max"] = self.add_fortune_point

        jsontext["data"]["status"].append({})
        jsontext["data"]["status"][4]["label"] = "ブレイク"
        jsontext["data"]["status"][4]["value"] = 1
        jsontext["data"]["status"][4]["max"] = 1

        i = 5
        jsontext["data"]["status"].append({})
        jsontext["data"]["status"][i]["label"] = self.specials_000
        jsontext["data"]["status"][i]["value"] = 1
        jsontext["data"]["status"][i]["max"] = 1
        i = i + 1

        jsontext["data"]["status"].append({})
        jsontext["data"]["status"][i]["label"] = self.specials_001
        jsontext["data"]["status"][i]["value"] = 1
        jsontext["data"]["status"][i]["max"] = 1
        i = i + 1

        jsontext["data"]["status"].append({})
        jsontext["data"]["status"][i]["label"] = self.specials_002
        jsontext["data"]["status"][i]["value"] = 1
        jsontext["data"]["status"][i]["max"] = 1
        i = i + 1

        if self.specials_003 != "":
            jsontext["data"]["status"].append({})
            jsontext["data"]["status"][i]["label"] = self.specials_003
            jsontext["data"]["status"][i]["value"] = 1
            jsontext["data"]["status"][i]["max"] = 1
            i = i + 1

        if self.specials_004 != "":
            jsontext["data"]["status"].append({})
            jsontext["data"]["status"][i]["label"] = self.specials_004
            jsontext["data"]["status"][i]["value"] = 1
            jsontext["data"]["status"][i]["max"] = 1
            i = i + 1

        for item in self.items:
            jsontext["data"]["status"].append({})
            jsontext["data"]["status"][i]["label"] = item
            jsontext["data"]["status"][i]["value"] = 1
            jsontext["data"]["status"][i]["max"] = 1
            i = i + 1

        jsontext["data"]["params"] = []

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][0]["label"] = "体力基本値"
        jsontext["data"]["params"][0]["value"] = self.strong_total

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][1]["label"] = "反射基本値"
        jsontext["data"]["params"][1]["value"] = self.sense_total

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][2]["label"] = "知覚基本値"
        jsontext["data"]["params"][2]["value"] = self.strong_total

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][3]["label"] = "理知基本値"
        jsontext["data"]["params"][3]["value"] = self.intellect_total

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][4]["label"] = "意志基本値"
        jsontext["data"]["params"][4]["value"] = self.will_total

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][5]["label"] = "幸運基本値"
        jsontext["data"]["params"][5]["value"] = self.bllesing_bonus

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][6]["label"] = "体力B"
        jsontext["data"]["params"][6]["value"] = self.strong_bonus

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][7]["label"] = "反射B"
        jsontext["data"]["params"][7]["value"] = self.sense_bonus

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][8]["label"] = "知覚B"
        jsontext["data"]["params"][8]["value"] = self.strong_bonus

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][9]["label"] = "理知B"
        jsontext["data"]["params"][9]["value"] = self.intellect_bonus

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][10]["label"] = "意志B"
        jsontext["data"]["params"][10]["value"] = self.will_bonus

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][11]["label"] = "幸運B"
        jsontext["data"]["params"][11]["value"] = self.bllesing_bonus

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][12]["label"] = "命中値"
        jsontext["data"]["params"][12]["value"] = self.outfits_total_hit

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][13]["label"] = "回避値"
        jsontext["data"]["params"][13]["value"] = self.outfits_total_dodge

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][14]["label"] = "魔導値"
        jsontext["data"]["params"][14]["value"] = self.outfits_total_magic

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][15]["label"] = "抗魔値"
        jsontext["data"]["params"][15]["value"] = self.outfits_total_countermagic

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][16]["label"] = "行動値"
        jsontext["data"]["params"][16]["value"] = self.outfits_total_action

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][17]["label"] = "移動力"
        jsontext["data"]["params"][17]["value"] = self.outfits_total_battlespeed_total

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][18]["label"] = "斬防御"
        jsontext["data"]["params"][18]["value"] = self.armourstotal_slash

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][19]["label"] = "刺防御"
        jsontext["data"]["params"][19]["value"] = self.armourstotal_pierce

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][20]["label"] = "殴防御"
        jsontext["data"]["params"][20]["value"] = self.armourstotal_crash

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][21]["label"] = "炎防御"
        jsontext["data"]["params"][21]["value"] = self.armourstotal_fire

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][22]["label"] = "氷防御"
        jsontext["data"]["params"][22]["value"] = self.armourstotal_ice

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][23]["label"] = "雷防御"
        jsontext["data"]["params"][23]["value"] = self.armourstotal_thunder

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][24]["label"] = "光防御"
        jsontext["data"]["params"][24]["value"] = self.armourstotal_light

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][25]["label"] = "闇防御"
        jsontext["data"]["params"][25]["value"] = self.armourstotal_dark

        outfits_rightattack_array = self.outfits_rightattack.split("+")
        outfits_leftattack_array = self.outfits_leftattack.split("+")
        outfits_magicrightattack_array = self.outfits_magicrightattack.split("+")
        outfits_magicleftattack_array = self.outfits_magicleftattack.split("+")

        jsontext["data"]["active"] = "true"
        jsontext["data"]["secret"] = "false"
        jsontext["data"]["invisible"] = "false"
        jsontext["data"]["hideStatus"] = "false"
        jsontext["data"]["commands"] = "//リソース\n" + \
                                       "C({HP}-YY)　残りHP\n" + \
                                       "C({MP}-YY)　残りMP\n\n" + \
                                       "//防御、+0欄に修正を記入\nAL+{回避値}+0　近・回避\n" \
                                       "AL+{抗魔値}+0　遠・抗魔\nC(XX-{}-0)　被ダメージ、{}内に防御属性3文字\n\n" \
                                       "//攻撃、+0欄に修正を記入\nAL+{命中値}+0　近・命中\nAL+{魔導値}+0　遠・魔導\n" + \
                                       "2d6+" + outfits_rightattack_array[1] + "+0　" + \
                                       "〈" + outfits_rightattack_array[0] + "〉" + \
                                       self.outfits_rightname + "ダメージ\n" \
                                       "2d6+" + outfits_leftattack_array[1] + "+0　" + \
                                       "〈" + outfits_leftattack_array[0] + "〉" + \
                                       self.outfits_leftname + "ダメージ\n" \
                                       "2d6+" + outfits_magicrightattack_array[1] + "+0　" + \
                                       "〈" + outfits_magicrightattack_array[0] + "〉" + \
                                       self.outfits_magicrightname + "ダメージ\n" \
                                       "2d6+" + outfits_magicleftattack_array[1] + "+0　" + \
                                       "〈" + outfits_magicleftattack_array[0] + "〉" + \
                                       self.outfits_magicleftname + "ダメージ\n" \
                                       "\n//能力値判定\nAL+{体力B}  体力判定\nAL+{反射B}  反射判定\nAL+{知覚B}  " \
                                       "知覚判定\nAL+{理知B}  理知判定\nAL+{意志B}  意志判定\nAL+{幸運B}  幸運判定"
        jsontext["data"]["externalUrl"] = self.url
        file_name = self.character_name + "_キャラクター駒データ.txt"

        with open(file_name, 'w', encoding="utf-8") as file:  # 第二引数：writableオプションを指定
            json.dump(jsontext, file)

        print("キャラクター駒データを生成しました")

    def output_text(self):
        self.output_pawn()
        #tkinter.messagebox.showinfo(title="完了", message="駒データを生成しました")

    def output_pawn(self):
        # 駒のココフォリア用データを出力する
        jsontext = {}
        jsontext["kind"] = "character"
        jsontext["data"] = {}
        jsontext["data"]["name"] = "バトルマスターサポート"
        jsontext["data"]["memo"] = "バトルマスターサポート操作用の駒です"
        jsontext["data"]["initiative"] = 0
        jsontext["data"]["status"] = []

        jsontext["data"]["status"].append({})
        jsontext["data"]["status"][0]["label"] = "HP"
        jsontext["data"]["status"][0]["value"] = "100"
        jsontext["data"]["status"][0]["max"] = "100"

        jsontext["data"]["active"] = "true"
        jsontext["data"]["secret"] = "false"
        jsontext["data"]["invisible"] = "false"
        jsontext["data"]["hideStatus"] = "false"
        jsontext["data"]["externalUrl"] = "https://elaunomitsugi.booth.pm/items/6174946"
        jsontext["data"]["commands"] = "戦闘マスタリング開始\n戦闘マスタリング再開\n戦闘マスタリング中断\n戦闘マスタリング終了\n" \
        "ソフトウェア終了\n勝利条件：\n初期配置完了\n最高行動値キャラクター：\n" \
        "イニシアチブプロセス開始\nメインプロセス開始：\nメインプロセス開始\n未行動なしです\n" \
        "メインプロセス終了\nセットアッププロセス開始\nセットアッププロセス終了\n" \
        "クリンナッププロセス開始\nクリンナッププロセス終了\n" \
        "\n勝利条件を達成しました\n攻撃します\n回避します\n" \
        "近接攻撃判定\n遠隔攻撃判定\n武器攻撃判定\n魔法攻撃判定\n特技を使用します\n" \
        "命中しました\n回避しました"
        file_name = self.character_name + "_未装備駒データ.txt"

        with open(file_name, 'w', encoding="utf-8") as file:  # 第二引数：writableオプションを指定
            json.dump(jsontext, file)

        print("未装備駒データを生成しました")


def get_data(value):
    """
    print("URL=" + value)
    url = value
    driver = webdriver.Chrome()
    driver.get(url)
    character = CharacterData()
    time.sleep(5)

    character.input_data(driver, url)
    character.output_text()

    driver.quit()
    """
    guardian = GuardianData()

    guardian.output_text()

    tkinter.messagebox.showinfo(title="完了", message="駒データを生成しました")


if __name__ == "__main__":
    root = tkinter.Tk()
    root.title(u"アルシャードセイヴァーRPG ココフォリア用駒データ作成ツール")
    root.geometry("400x150")

    # ラベル
    Static1 = tkinter.Label(text=u'キャラクターシートURL\nhttps://character-sheets.appspot.com/al2/')
    Static1.pack()

    # エントリー
    EditBox = tkinter.Entry()
    EditBox.pack()

    Button1 = tkinter.Button(text=u'生成', command=lambda: [get_data(EditBox.get())])
    Button1.pack()

    # ボタン
    Button2 = tkinter.Button(text=u'終了', command=lambda: root.quit())
    Button2.pack()

    root.mainloop()