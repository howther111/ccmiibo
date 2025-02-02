#!/usr/bin/env python
# -*- coding: utf8 -*-
import random
import sys
import tkinter
import tkinter.messagebox
import tkinter.ttk as ttk
import time
import json
import CreateMachineNumber
import CreatePetName
import CreatePilotName
import create_weapon

class GuardianData():
    size_list = ["S", "M", "M", "M", "L"]
    special_list = ["トール", "オーディン", "フツノミタマ", "タケミカヅチ"
        , "ヘイムダル", "エーギル", "バルドル", "ヘル", "アカラナータ", "ニョルド", "ネルガル"
        , "ミューズ", "スィン", "ティール", "ヘルモード", "ルドラ"]
    character_name = ""
    guardian_name = ""
    guardian_type = ""
    guardian_type_list = ["モブ", "ソロ", "強敵"]
    guardian_class = ""
    guardian_class_list = ["奈落獣", "艦船", "ミーレス（マシンザウルス）", "アビスミーレス（マシンザウルス）",
                           "ガーディアン（マシンザウルス）", "アビスガーディアン（マシンザウルス）",
                           "ミーレス（カバリエ）", "アビスミーレス（カバリエ）",
                           "ガーディアン（カバリエ）", "アビスガーディアン（カバリエ）"]
    level = 0
    guardian_size = ""
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
    add_fortune_point = 0
    outfits_total_hit = 0
    outfits_total_dodge = 0
    outfits_total_magic = 0
    outfits_total_countermagic = 0
    outfits_total_action = 0
    outfits_total_fp = 0
    outfits_total_hp = 0
    outfits_total_mp = 0
    outfits_total_attack = 0
    outfits_total_battlespeed_total = ""

    outfits_main_weapon_shortname = ""
    outfits_main_weapon_shortattack = ""
    outfits_main_weapon_shortrange = ""
    outfits_main_weapon_shortstrong = "なし"

    outfits_sub_weapon_shortname = ""
    outfits_sub_weapon_shortattack = ""
    outfits_sub_weapon_shortrange = ""
    outfits_sub_weapon_shortstrong = "なし"

    outfits_main_weapon_longname = ""
    outfits_main_weapon_longattack = ""
    outfits_main_weapon_longrange = ""
    outfits_main_weapon_longstrong = "なし"

    outfits_sub_weapon_longname = ""
    outfits_sub_weapon_longattack = ""
    outfits_sub_weapon_longrange = ""
    outfits_sub_weapon_longstrong = "なし"

    armourstotal_slash = 0
    armourstotal_pierce = 0
    armourstotal_crash = 0
    armourstotal_fire = 0
    armourstotal_ice = 0
    armourstotal_thunder = 0
    armourstotal_light = 0
    armourstotal_dark = 0

    items = []
    specials = []

    break_flg = 0

    url = ""

    def input_data(self, level=5, guardian_type="ソロ", guardian_class="奈落獣"):
        self.guardian_type = guardian_type
        self.guardian_class = guardian_class
        self.url = "https://elaunomitsugi.booth.pm/items/6432109"

        if guardian_class == "奈落獣":
            self.character_name = "奈落獣" + CreatePilotName.CreatePilotName()
            self.guardian_name = self.character_name
        elif guardian_class == "艦船":
            ship_list = ["駆逐艦", "巡洋艦", "軽巡洋艦", "重巡洋艦", "戦艦", "空母", "強襲揚陸艦"]
            self.character_name = CreatePilotName.CreatePilotName() + "・" + CreatePilotName.CreatePilotName()
            self.guardian_name = ship_list[random.randint(0, len(ship_list) - 1)] + CreatePetName.CreatePetName()
        elif guardian_class == "ミーレス（マシンザウルス）" or guardian_class == "ガーディアン（マシンザウルス）" or guardian_class == "アビスミーレス（マシンザウルス）"or guardian_class == "アビスガーディアン（マシンザウルス）":
            self.character_name = CreatePilotName.CreatePilotName() + "・" + CreatePilotName.CreatePilotName()
            self.guardian_name = "機械恐竜" + CreatePilotName.CreatePilotName()
        elif guardian_class == "ドラゴン":
            self.character_name = CreatePilotName.CreatePilotName() + "ドラゴン"
            self.guardian_name = self.character_name
        else:
            self.character_name = CreatePilotName.CreatePilotName() + "・" + CreatePilotName.CreatePilotName()
            self.guardian_name = CreateMachineNumber.CreateMachineNumber() + " " + CreatePetName.CreatePetName()

        self.guardian_type = guardian_type
        self.level = level
        self.guardian_size = self.size_list[random.randint(0, len(self.size_list) - 1)]
        if guardian_class == "艦船":
            self.guardian_size = "XL"

        self.player_name = "エネミー"
        self.strong_total = 3 + max(0, random.randint(0,6) + random.randint(0, self.level))
        self.strong_bonus = int(self.strong_total / 3)
        self.reflex_total = 3 + max(0, random.randint(0,6) + random.randint(0, self.level))
        self.reflex_bonus = int(self.reflex_total / 3)
        self.sense_total = 3 + max(0, random.randint(0,6) + random.randint(0, self.level))
        self.sense_bonus = int(self.sense_total / 3)
        self.intellect_total = 3 + max(0, random.randint(0,6) + random.randint(0, self.level))
        self.intellect_bonus = int(self.intellect_total / 3)
        self.will_total = 3 + max(0, random.randint(0,6) + random.randint(0, self.level))
        self.will_bonus = int(self.will_total / 3)
        self.bllesing_total = 3 + max(0, random.randint(0,6) + random.randint(0, self.level))
        self.bllesing_bonus = int(self.bllesing_total / 3)

        special_num = 0
        if guardian_class == "ガーディアン（カバリエ）" or guardian_class == "ガーディアン（マシンザウルス）":
            special_num = 3
        elif guardian_class == "アビスガーディアン（カバリエ）" or guardian_class == "アビスガーディアン（マシンザウルス）":
            special_num = max(3, (random.randint(0, self.level) * 2) - random.randint(0, self.level))

        if special_num > 0:
            self.specials.append(self.special_list[random.randint(0, len(self.special_list) - 1)])

            for i in range(special_num - 1):
                try:
                    specialnum = i + 1
                    specialstr = "specials." + str(specialnum).zfill(3) + ".name"
                    self.specials.append(self.special_list[random.randint(0, len(self.special_list) - 1)])
                except:
                    pass

        self.outfits_total_hit = 7 + max(0, (random.randint(0, self.level) * 2) - random.randint(0, self.level))
        self.outfits_total_dodge = 1 + max(0, (random.randint(0, self.level) * 2) - random.randint(0, self.level))
        self.outfits_total_magic = 7 + max(0, (random.randint(0, self.level) * 2) - random.randint(0, self.level))
        self.outfits_total_countermagic = 1 + max(0,
                                                  (random.randint(0, self.level) * 2) - random.randint(0, self.level))
        self.outfits_total_action = 4 + max(0, (random.randint(0, self.level) * 2) - random.randint(0, self.level))
        if self.guardian_type == "モブ":
            self.outfits_total_fp = max(10,
                                        (random.randint(self.level - 2, self.level) * 10) + (random.randint(1, 10) * 1))
        elif self.guardian_type == "ソロ":
            self.outfits_total_fp = max(5,
                                        (random.randint(self.level - 2, self.level) * 7) + (random.randint(1, 7) * 1))
        elif self.guardian_type == "強敵":
            self.outfits_total_fp = max(50,
                                        (random.randint(self.level - 2, self.level) * 20) + (random.randint(1, 20) * 1))
        self.outfits_total_hp = max(10, (random.randint(self.level - 2, self.level) * 5) + (random.randint(1, 5) * 1))
        self.outfits_total_mp = max(10, (random.randint(self.level - 2, self.level) * 5) + (random.randint(1, 5) * 1))
        self.outfits_total_battlespeed_total = max(1, int(3 + int((random.randint(0, self.level) * 0.3)) - int(
            (random.randint(0, self.level) * 0.2)))) * 5
        #self.outfits_total_battlespeed_total = self.outfits_total_battlespeed_total.replace("ﾏｽ", "")

        self.add_fortune_point = 0

        weapon_weapon_type = ""
        while weapon_weapon_type == "砲撃" or weapon_weapon_type == "":
            main_weapon = create_weapon.create_weapon(self.level)
            self.outfits_main_weapon_shortname = main_weapon.weapon_name
            self.outfits_main_weapon_shortattack = main_weapon.element + "+" + str(main_weapon.attack)
            self.outfits_main_weapon_shortrange = str(main_weapon.max_range) + "m"
            self.outfits_main_weapon_shorttarget = main_weapon.target
            weapon_weapon_type = main_weapon.weapon_type

        weapon_weapon_type = ""
        while weapon_weapon_type == "砲撃" or weapon_weapon_type == "":
            sub_weapon = create_weapon.create_weapon(self.level)
            self.outfits_sub_weapon_shortname = sub_weapon.weapon_name
            self.outfits_sub_weapon_shortattack = sub_weapon.element + "+" + str(sub_weapon.attack)
            self.outfits_sub_weapon_shortrange = str(sub_weapon.max_range) + "m"
            self.outfits_sub_weapon_shorttarget = sub_weapon.target
            weapon_weapon_type = sub_weapon.weapon_type

        weapon_weapon_type = ""
        while weapon_weapon_type == "白兵" or weapon_weapon_type == "射撃" or weapon_weapon_type == "":
            main_weapon = create_weapon.create_weapon(self.level)
            self.outfits_main_weapon_longname = main_weapon.weapon_name
            self.outfits_main_weapon_longattack = main_weapon.element + "+" + str(main_weapon.attack)
            self.outfits_main_weapon_longrange = str(main_weapon.max_range) + "m"
            self.outfits_main_weapon_longtarget = main_weapon.target
            weapon_weapon_type = main_weapon.weapon_type

        weapon_weapon_type = ""
        while weapon_weapon_type == "白兵" or weapon_weapon_type == "射撃" or weapon_weapon_type == "":
            sub_weapon = create_weapon.create_weapon(self.level)
            self.outfits_sub_weapon_longname = sub_weapon.weapon_name
            self.outfits_sub_weapon_longattack = sub_weapon.element + "+" + str(sub_weapon.attack)
            self.outfits_sub_weapon_longrange = str(sub_weapon.max_range) + "m"
            self.outfits_sub_weapon_longtarget = sub_weapon.target
            weapon_weapon_type = sub_weapon.weapon_type

        self.armourstotal_slash = random.randint(0, self.level)
        self.armourstotal_pierce = random.randint(0, self.level)
        self.armourstotal_crash = random.randint(0, self.level)
        self.armourstotal_fire = random.randint(0, self.level)
        self.armourstotal_ice = random.randint(0, self.level)
        self.armourstotal_thunder = random.randint(0, self.level)
        self.armourstotal_light = random.randint(0, self.level)
        self.armourstotal_dark = random.randint(0, self.level)

        print(self.guardian_name)

    def output_text(self):
        # 駒のテキストデータを出力する
        text = "ガーディアン:" + self.guardian_name + "\n" + \
                   "PC:" + self.character_name +  \
                   " PL:" + self.player_name + "\n" + \
                   "レベル:" + str(self.level) + \
                   " サイズ:" + self.guardian_size + "\n"\
                   "分類:" + self.guardian_type + \
                   " クラス:" + self.guardian_class

        #text = text + "\n財産ポイント:" + self.add_fortune_point

        text = text + "\n【命中】" + str(self.outfits_total_hit) + \
                   "【回避】" + str(self.outfits_total_dodge) + \
                   "【砲撃】" + str(self.outfits_total_magic) + \
                   "【防壁】" + str(self.outfits_total_countermagic) + \
                   "【行動】" + str(self.outfits_total_action) + \
                   "\n【HP】" + str(self.outfits_total_fp) + \
                   "【MP】" + str(self.outfits_total_mp) + \
                   "【移動力】" + str(self.outfits_total_battlespeed_total)

        text = text + "\n加護:"
        if (len(self.specials) == 0):
            text = text + "なし" + "/"
        for special in self.specials:
            text = text + special + "/"
        text = text[:-1]

        text = text + "\n[*]主近:" + self.outfits_main_weapon_shortname + \
                " 射程:" + self.outfits_main_weapon_shortrange + \
                " 代償:" + self.outfits_main_weapon_shortstrong + \
                "\n攻撃力:" + self.outfits_main_weapon_shortattack + \
                " 対象:" + self.outfits_main_weapon_shorttarget

        text = text + "\n[*]副近:" + self.outfits_sub_weapon_shortname + \
                " 射程:" + self.outfits_sub_weapon_shortrange + \
                " 代償:" + self.outfits_sub_weapon_shortstrong + \
                "\n攻撃力:" + self.outfits_sub_weapon_shortattack + \
                " 対象:" + self.outfits_sub_weapon_shorttarget

        text = text + "\n[*]主遠:" + self.outfits_main_weapon_longname + \
                   " 射程:" + self.outfits_main_weapon_longrange + \
                   " 代償:" + self.outfits_main_weapon_longstrong + \
                   "\n攻撃力:" + self.outfits_main_weapon_longattack + \
                   " 対象:" + self.outfits_main_weapon_longtarget

        text = text + "\n[*]副遠:" + self.outfits_sub_weapon_longname + \
                   " 射程:" + self.outfits_sub_weapon_longrange + \
                   " 代償:" + self.outfits_sub_weapon_longstrong + \
                   "\n攻撃力:" + self.outfits_sub_weapon_longattack + \
                   " 対象:" + self.outfits_sub_weapon_longtarget

        text = text + "\n防御力:斬" + str(self.armourstotal_slash) + \
                "/刺" + str(self.armourstotal_pierce) + \
                "/殴" + str(self.armourstotal_crash) + \
                "/炎" + str(self.armourstotal_fire) + \
                "/氷" + str(self.armourstotal_ice) + \
                "/雷" + str(self.armourstotal_thunder) + \
                "/光" + str(self.armourstotal_light) + \
                "/闇" + str(self.armourstotal_dark)

        print(text)

        file_name = self.guardian_name + "_ガーディアンテキストデータ.txt"

        f = open(file_name, 'w', encoding="utf-8")
        f.write(text)
        f.close()

        print("ガーディアンテキストデータを生成しました")
        self.output_pawn(text)

    def output_online_json_data(self):
        self.outfits_main_weapon_shortattack_array = self.outfits_main_weapon_shortattack.split("+")
        self.outfits_sub_weapon_shortattack_array = self.outfits_sub_weapon_shortattack.split("+")
        self.outfits_main_weapon_longattack_array = self.outfits_main_weapon_longattack.split("+")
        self.outfits_sub_weapon_longattack_array = self.outfits_sub_weapon_longattack.split("+")

        jsontext = {}
        jsontext["data"] = {}
        jsontext["data"]["guardian_name"] = self.guardian_name
        jsontext["data"]["character_name"] = self.character_name
        jsontext["data"]["player_name"] = self.player_name
        jsontext["data"]["level"] = max(0, int(self.level))
        jsontext["data"]["size"] = self.guardian_size
        jsontext["data"]["hit"] = max(0, int(self.outfits_total_hit))
        jsontext["data"]["dodge"] = max(0, int(self.outfits_total_dodge))
        jsontext["data"]["magic"] = max(0, int(self.outfits_total_magic))
        jsontext["data"]["countermagic"] = max(0, int(self.outfits_total_countermagic))
        jsontext["data"]["action"] = max(0, int(self.outfits_total_action))
        jsontext["data"]["fp"] = max(0, int(self.outfits_total_fp))
        jsontext["data"]["hp"] = max(0, int(self.outfits_total_hp))
        jsontext["data"]["mp"] = max(0, int(self.outfits_total_mp))
        jsontext["data"]["battlespeed"] = max(0, int(self.outfits_total_battlespeed_total))
        jsontext["data"]["mws_name"] = self.outfits_main_weapon_shortname

        if self.outfits_main_weapon_shortrange == "":
            jsontext["data"]["mws_shortrange"] = 0
            jsontext["data"]["mws_longrange"] = 0
        else:
            jsontext["data"]["mws_shortrange"] = int(self.outfits_main_weapon_shortrange[:1])
            jsontext["data"]["mws_longrange"] = int(self.outfits_main_weapon_shortrange[-1:])

        jsontext["data"]["mws_attack"] = max(0, int(self.outfits_main_weapon_shortattack_array[1]))
        jsontext["data"]["mws_element"] = self.outfits_main_weapon_shortattack_array[0]
        jsontext["data"]["sws_name"] = self.outfits_sub_weapon_shortname

        if self.outfits_sub_weapon_shortrange == "":
            jsontext["data"]["sws_shortrange"] = 0
            jsontext["data"]["sws_longrange"] = 0
        else:
            jsontext["data"]["sws_shortrange"] = int(self.outfits_sub_weapon_shortrange[:1])
            jsontext["data"]["sws_longrange"] = int(self.outfits_sub_weapon_shortrange[-1:])

        jsontext["data"]["sws_attack"] = max(0, int(self.outfits_sub_weapon_shortattack_array[1]))
        jsontext["data"]["sws_element"] = self.outfits_sub_weapon_shortattack_array[0]
        jsontext["data"]["mwl_name"] = self.outfits_main_weapon_longname

        if self.outfits_main_weapon_longrange == "":
            jsontext["data"]["mwl_shortrange"] = 0
            jsontext["data"]["mwl_longrange"] = 0
        else:
            jsontext["data"]["mwl_shortrange"] = int(self.outfits_main_weapon_longrange[:1])
            jsontext["data"]["mwl_longrange"] = int(self.outfits_main_weapon_longrange[-1:])

        jsontext["data"]["mwl_attack"] = max(0, int(self.outfits_main_weapon_longattack_array[1]))
        jsontext["data"]["mwl_element"] = self.outfits_main_weapon_longattack_array[0]
        jsontext["data"]["swl_name"] = self.outfits_sub_weapon_longname

        if self.outfits_sub_weapon_longrange == "":
            jsontext["data"]["swl_shortrange"] = 0
            jsontext["data"]["swl_longrange"] = 0
        else:
            jsontext["data"]["swl_shortrange"] = int(self.outfits_sub_weapon_longrange[:1])
            jsontext["data"]["swl_longrange"] = int(self.outfits_sub_weapon_longrange[-1:])

        jsontext["data"]["swl_attack"] = max(0, int(self.outfits_sub_weapon_longattack_array[1]))
        jsontext["data"]["swl_element"] = self.outfits_sub_weapon_longattack_array[0]
        jsontext["data"]["armourstotal_slash"] = max(0, int(self.armourstotal_slash))
        jsontext["data"]["armourstotal_pierce"] = max(0, int(self.armourstotal_pierce))
        jsontext["data"]["armourstotal_crash"] = max(0, int(self.armourstotal_crash))
        jsontext["data"]["armourstotal_fire"] = max(0, int(self.armourstotal_fire))
        jsontext["data"]["armourstotal_ice"] = max(0, int(self.armourstotal_ice))
        jsontext["data"]["armourstotal_thunder"] = max(0, int(self.armourstotal_thunder))
        jsontext["data"]["armourstotal_light"] = max(0, int(self.armourstotal_light))
        jsontext["data"]["armourstotal_dark"] = max(0, int(self.armourstotal_dark))
        jsontext["data"]["cost"] = (jsontext["data"]["hit"] * 100)
        jsontext["data"]["cost"] = (jsontext["data"]["dodge"] * 100) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (jsontext["data"]["magic"] * 100) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (jsontext["data"]["countermagic"] * 100) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (jsontext["data"]["action"] * 100) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (jsontext["data"]["fp"] * 10) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (jsontext["data"]["hp"] * 10) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (jsontext["data"]["mp"] * 10) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (jsontext["data"]["battlespeed"] * 200) +  jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (min(10, max(0, jsontext["data"]["mws_longrange"])) * 200) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (min(10, max(0, jsontext["data"]["mws_shortrange"])) * -100) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (jsontext["data"]["mws_attack"] * 100) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (min(10, max(0, jsontext["data"]["sws_longrange"])) * 200) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (min(10, max(0, jsontext["data"]["sws_shortrange"])) * -100) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (jsontext["data"]["sws_attack"] * 100) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (min(10, max(0, jsontext["data"]["mwl_longrange"])) * 200) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (min(10, max(0, jsontext["data"]["mwl_shortrange"])) * -100) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (jsontext["data"]["mwl_attack"] * 100) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (min(10, max(0, jsontext["data"]["swl_longrange"])) * 200) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (min(10, max(0, jsontext["data"]["swl_shortrange"])) * -100) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (jsontext["data"]["swl_attack"] * 100) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (jsontext["data"]["armourstotal_slash"] * 50) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (jsontext["data"]["armourstotal_pierce"] * 50) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (jsontext["data"]["armourstotal_crash"] * 50) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (jsontext["data"]["armourstotal_fire"] * 50) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (jsontext["data"]["armourstotal_ice"] * 50) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (jsontext["data"]["armourstotal_thunder"] * 50) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (jsontext["data"]["armourstotal_light"] * 50) + jsontext["data"]["cost"]
        jsontext["data"]["cost"] = (jsontext["data"]["armourstotal_dark"] * 50) + jsontext["data"]["cost"]

        # 出力
        file_name = self.guardian_name + "_ガーディアンオンラインデータ.txt"

        f = open(file_name, 'w', encoding="utf-8")
        f.write(json.dumps(jsontext, indent=4, ensure_ascii=False))
        f.close()

        print("ガーディアンオンラインデータを生成しました")

    def output_pawn(self, text_data):
        # 駒のココフォリア用データを出力する
        jsontext = {}
        jsontext["kind"] = "character"
        jsontext["data"] = {}
        jsontext["data"]["name"] = self.guardian_name
        jsontext["data"]["memo"] = text_data
        jsontext["data"]["initiative"] = int(self.outfits_total_action)
        jsontext["data"]["status"] = []

        jsontext["data"]["status"].append({})
        jsontext["data"]["status"][0]["label"] = "FP"
        jsontext["data"]["status"][0]["value"] = self.outfits_total_fp
        jsontext["data"]["status"][0]["max"] = self.outfits_total_fp

        jsontext["data"]["status"].append({})
        jsontext["data"]["status"][1]["label"] = "HP"
        jsontext["data"]["status"][1]["value"] = self.outfits_total_hp
        jsontext["data"]["status"][1]["max"] = self.outfits_total_hp

        jsontext["data"]["status"].append({})
        jsontext["data"]["status"][2]["label"] = "EN"
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

        for special in self.specials:
            jsontext["data"]["status"].append({})
            jsontext["data"]["status"][i]["label"] = special
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
        jsontext["data"]["params"][0]["value"] = str(self.strong_total)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][1]["label"] = "反射基本値"
        jsontext["data"]["params"][1]["value"] = str(self.sense_total)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][2]["label"] = "知覚基本値"
        jsontext["data"]["params"][2]["value"] = str(self.strong_total)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][3]["label"] = "理知基本値"
        jsontext["data"]["params"][3]["value"] = str(self.intellect_total)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][4]["label"] = "意志基本値"
        jsontext["data"]["params"][4]["value"] = str(self.will_total)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][5]["label"] = "幸運基本値"
        jsontext["data"]["params"][5]["value"] = str(self.bllesing_bonus)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][6]["label"] = "体力B"
        jsontext["data"]["params"][6]["value"] = str(self.strong_bonus)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][7]["label"] = "反射B"
        jsontext["data"]["params"][7]["value"] = str(self.sense_bonus)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][8]["label"] = "知覚B"
        jsontext["data"]["params"][8]["value"] = str(self.strong_bonus)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][9]["label"] = "理知B"
        jsontext["data"]["params"][9]["value"] = str(self.intellect_bonus)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][10]["label"] = "意志B"
        jsontext["data"]["params"][10]["value"] = str(self.will_bonus)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][11]["label"] = "幸運B"
        jsontext["data"]["params"][11]["value"] = str(self.bllesing_bonus)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][12]["label"] = "命中値"
        jsontext["data"]["params"][12]["value"] = str(self.outfits_total_hit)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][13]["label"] = "回避値"
        jsontext["data"]["params"][13]["value"] = str(self.outfits_total_dodge)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][14]["label"] = "砲撃値"
        jsontext["data"]["params"][14]["value"] = str(self.outfits_total_magic)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][15]["label"] = "防壁値"
        jsontext["data"]["params"][15]["value"] = str(self.outfits_total_countermagic)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][16]["label"] = "行動値"
        jsontext["data"]["params"][16]["value"] = str(self.outfits_total_action)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][17]["label"] = "移動力"
        jsontext["data"]["params"][17]["value"] = str(self.outfits_total_battlespeed_total)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][18]["label"] = "斬防御"
        jsontext["data"]["params"][18]["value"] = str(self.armourstotal_slash)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][19]["label"] = "刺防御"
        jsontext["data"]["params"][19]["value"] = str(self.armourstotal_pierce)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][20]["label"] = "殴防御"
        jsontext["data"]["params"][20]["value"] = str(self.armourstotal_crash)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][21]["label"] = "炎防御"
        jsontext["data"]["params"][21]["value"] = str(self.armourstotal_fire)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][22]["label"] = "氷防御"
        jsontext["data"]["params"][22]["value"] = str(self.armourstotal_ice)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][23]["label"] = "雷防御"
        jsontext["data"]["params"][23]["value"] = str(self.armourstotal_thunder)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][24]["label"] = "光防御"
        jsontext["data"]["params"][24]["value"] = str(self.armourstotal_light)

        jsontext["data"]["params"].append({})
        jsontext["data"]["params"][25]["label"] = "闇防御"
        jsontext["data"]["params"][25]["value"] = str(self.armourstotal_dark)

        outfits_main_weapon_shortattack_array = self.outfits_main_weapon_shortattack.split("+")
        outfits_sub_weapon_shortattack_array = self.outfits_sub_weapon_shortattack.split("+")
        outfits_main_weapon_longattack_array = self.outfits_main_weapon_longattack.split("+")
        outfits_sub_weapon_longattack_array = self.outfits_sub_weapon_longattack.split("+")

        jsontext["data"]["active"] = "true"
        jsontext["data"]["secret"] = "false"
        jsontext["data"]["invisible"] = "false"
        jsontext["data"]["hideStatus"] = "false"
        jsontext["data"]["commands"] = "//リソース\n" + \
                                       "C({FP}-YY)　残りFP\n" + \
                                       "C({HP}-YY)　残りHP\n" + \
                                       "C({EN}-YY)　残りEN\n\n" + \
                                       "//防御、+0欄に修正を記入\nMG+{回避値}+0　近・回避\n" \
                                       "MG+{防壁値}+0　遠・防壁\nC(XX-{}-0)　被ダメージ、{}内に防御属性3文字\n\n" \
                                       "//攻撃、+0欄に修正を記入\nMG+{命中値}+0　近・命中\nMG+{砲撃値}+0　遠・砲撃\n" + \
                                       "2d6+" + outfits_main_weapon_shortattack_array[1] + "+0　" + \
                                       "〈" + outfits_main_weapon_shortattack_array[0] + "〉" + \
                                       self.outfits_main_weapon_shortname + "ダメージ\n" \
                                       "2d6+" + outfits_sub_weapon_shortattack_array[1] + "+0　" + \
                                       "〈" + outfits_sub_weapon_shortattack_array[0] + "〉" + \
                                       self.outfits_sub_weapon_shortname + "ダメージ\n" \
                                       "2d6+" + outfits_main_weapon_longattack_array[1] + "+0　" + \
                                       "〈" + outfits_main_weapon_longattack_array[0] + "〉" + \
                                       self.outfits_main_weapon_longname + "ダメージ\n" \
                                       "2d6+" + outfits_sub_weapon_longattack_array[1] + "+0　" + \
                                       "〈" + outfits_sub_weapon_longattack_array[0] + "〉" + \
                                       self.outfits_sub_weapon_longname + "ダメージ\n" \
                                       "\n//能力値判定\nMG+{体力B}  体力判定\nMG+{反射B}  反射判定\nMG+{知覚B}  " \
                                       "知覚判定\nMG+{理知B}  理知判定\nMG+{意志B}  意志判定\nMG+{幸運B}  幸運判定"
        jsontext["data"]["externalUrl"] = self.url
        file_name = self.guardian_name + "_ガーディアン駒データ.txt"

        with open(file_name, 'w', encoding="utf-8") as file:  # 第二引数：writableオプションを指定
            json.dump(jsontext, file, ensure_ascii=False)

        print("ガーディアン駒データを生成しました")

    def output_prompt_guardian(self, image_type="人型ロボット"):
        text = "文字を描くことなく、以下の特徴を持つ" + image_type + "の全身像を描いてください。 " + \
        "背景：白 カラーリング：自由 " + \
        "右腕武装：" + self.outfits_main_weapon_shortname + " " + \
        "左腕武装：" + self.outfits_sub_weapon_shortname + " " + \
        "右肩武装：" + self.outfits_main_weapon_longname + " " + \
        "左肩武装：" + self.outfits_sub_weapon_longname
        file_name = self.guardian_name + "_ガーディアンプロンプトデータ.txt"

        f = open(file_name, 'w', encoding="utf-8")
        f.write(text)
        f.close()

        print("ガーディアンプロンプトデータを生成しました")

def get_data(level=3, guardian_type="ソロ", guardian_class="ミーレス（カバリエ）"):
    guardian = GuardianData()
    time.sleep(5)

    guardian.input_data(level=level, guardian_type=guardian_type, guardian_class=guardian_class)
    guardian.output_text()
    if guardian_class == "奈落獣":
        guardian.output_prompt_guardian(image_type="怪獣")
    elif guardian_class == "艦船":
        guardian.output_prompt_guardian(image_type="宇宙戦艦")
    elif guardian_class == "ミーレス（マシンザウルス）" or guardian_class == "アビスミーレス（マシンザウルス）" or guardian_class == "ガーディアン（マシンザウルス）" or guardian_class == "アビスガーディアン（マシンザウルス）":
        guardian.output_prompt_guardian(image_type="機械恐竜")
    else:
        guardian.output_prompt_guardian(image_type="モビルスーツ")

    #guardian.output_online_json_data()

    tkinter.messagebox.showinfo(title="完了", message="駒データを生成しました")

    sys.exit()


if __name__ == "__main__":
    root = tkinter.Tk()
    root.title(u"メタリックガーディアンRPG ココフォリア用エネミーデータ作成ツール")
    root.geometry("400x200")

    frame1 = tkinter.Frame(root, width=200, height=50)  # Button, Entry
    frame2 = tkinter.Frame(root, width=200, height=50)  # Button, Entry
    frame3 = tkinter.Frame(root, width=200, height=50)  # Button, Entry
    frame4 = tkinter.Frame(root, width=200, height=50)  # Button, Entry
    frame5 = tkinter.Frame(root, width=200, height=50)  # Button, Entry
    frame6 = tkinter.Frame(root, width=200, height=50)  # Button, Entry
    frame7 = tkinter.Frame(root, width=200, height=50)  # Button, Entry
    frame8 = tkinter.Frame(root, width=200, height=50)  # Button, Entry

    frame1.propagate(False)
    frame2.propagate(False)
    frame3.propagate(False)
    frame4.propagate(False)
    frame5.propagate(False)
    frame6.propagate(False)
    frame7.propagate(False)
    frame8.propagate(False)

    # Frameを配置（grid）
    frame1.grid(row=0, column=0)
    frame2.grid(row=0, column=1)
    frame3.grid(row=1, column=0)
    frame4.grid(row=1, column=1)
    frame5.grid(row=2, column=0)
    frame6.grid(row=2, column=1)
    frame7.grid(row=3, column=0)
    frame8.grid(row=3, column=1)

    # ラベル
    Static1 = tkinter.Label(frame1, text=u'レベル')
    Static1.pack()

    # エントリー
    EditBox = tkinter.Entry(frame2, width=25)
    EditBox.pack()

    # ラベル
    Static2 = tkinter.Label(frame3, text=u'分類')
    Static2.pack()

    # エントリー
    ComboBox1 = ttk.Combobox(frame4, width=25, values=["モブ", "ソロ", "強敵"])
    ComboBox1.pack()

    # ラベル
    Static3 = tkinter.Label(frame5, text=u'クラス')
    Static3.pack()

    # エントリー
    ComboBox2 = ttk.Combobox(frame6, width=25, values=["奈落獣", "艦船", "ミーレス（マシンザウルス）",
                                                       "アビスミーレス（マシンザウルス）", "ガーディアン（マシンザウルス）",
                                                       "アビスガーディアン（マシンザウルス）", "ミーレス（カバリエ）",
                                                       "アビスミーレス（カバリエ）", "ガーディアン（カバリエ）",
                                                       "アビスガーディアン（カバリエ）"])
    ComboBox2.pack()

    Button1 = tkinter.Button(frame7, text=u'生成', command=lambda: [get_data(int(EditBox.get()), ComboBox1.get(), ComboBox2.get())])
    Button1.pack()

    # ボタン
    Button2 = tkinter.Button(frame8, text=u'終了', command=lambda: root.quit())
    Button2.pack()

    root.mainloop()