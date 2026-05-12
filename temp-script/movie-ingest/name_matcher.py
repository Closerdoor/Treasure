# -*- coding: utf-8 -*-
"""
名字匹配工具

支持多种匹配策略：
1. 英文名精确匹配
2. 英文名模糊匹配（去除空格、标点）
3. 姓名倒序匹配
4. 中文名音译匹配
"""
import re
import unicodedata
from typing import Dict, List, Optional, Tuple


# 常见英文姓名音译对照表
NAME_TRANSLITERATION = {
    # A
    'adam': '亚当',
    'alan': '艾伦',
    'alex': '亚历克斯',
    'alexander': '亚历山大',
    'alice': '爱丽丝',
    'amanda': '阿曼达',
    'amy': '艾米',
    'andrew': '安德鲁',
    'angela': '安吉拉',
    'anna': '安娜',
    'anthony': '安东尼',
    'arthur': '亚瑟',
    
    # B
    'barbara': '芭芭拉',
    'ben': '本',
    'benjamin': '本杰明',
    'bill': '比尔',
    'billy': '比利',
    'bob': '鲍勃',
    'brian': '布莱恩',
    'bruce': '布鲁斯',
    
    # C
    'carl': '卡尔',
    'carol': '卡罗尔',
    'catherine': '凯瑟琳',
    'charles': '查尔斯',
    'chris': '克里斯',
    'christian': '克里斯蒂安',
    'christopher': '克里斯托弗',
    'claire': '克莱尔',
    'clark': '克拉克',
    'clifford': '克利福德',
    'clint': '克林特',
    'colin': '科林',
    
    # D
    'daniel': '丹尼尔',
    'david': '大卫',
    'dennis': '丹尼斯',
    'derek': '德里克',
    'dick': '迪克',
    'donald': '唐纳德',
    'douglas': '道格拉斯',
    
    # E
    'edward': '爱德华',
    'elizabeth': '伊丽莎白',
    'emily': '艾米丽',
    'emma': '艾玛',
    'eric': '埃里克',
    'eugene': '尤金',
    'eve': '伊芙',
    'evan': '埃文',
    
    # F
    'frank': '弗兰克',
    'frederick': '弗雷德里克',
    
    # G
    'gary': '加里',
    'george': '乔治',
    'gerald': '杰拉尔德',
    'gilbert': '吉尔伯特',
    'grace': '格蕾丝',
    'graham': '格雷厄姆',
    'gregory': '格雷戈里',
    
    # H
    'hans': '汉斯',
    'harry': '哈里',
    'helen': '海伦',
    'henry': '亨利',
    'howard': '霍华德',
    
    # I
    'ian': '伊恩',
    'irene': '艾琳',
    
    # J
    'jack': '杰克',
    'jacob': '雅各布',
    'james': '詹姆斯',
    'jason': '杰森',
    'jeffrey': '杰弗里',
    'jennifer': '珍妮弗',
    'jeremy': '杰里米',
    'jerry': '杰瑞',
    'jesse': '杰西',
    'jessica': '杰西卡',
    'jim': '吉姆',
    'jimmy': '吉米',
    'joan': '琼',
    'joanne': '乔安妮',
    'joe': '乔',
    'john': '约翰',
    'johnny': '约翰尼',
    'jonathan': '乔纳森',
    'joseph': '约瑟夫',
    'josh': '乔什',
    'joshua': '约书亚',
    'julia': '朱莉娅',
    'julie': '朱莉',
    'justin': '贾斯汀',
    
    # K
    'karen': '凯伦',
    'kate': '凯特',
    'katherine': '凯瑟琳',
    'katie': '凯蒂',
    'keith': '基思',
    'kenneth': '肯尼思',
    'kevin': '凯文',
    'kim': '金',
    'kyle': '凯尔',
    
    # L
    'larry': '拉里',
    'laura': '劳拉',
    'lawrence': '劳伦斯',
    'leonard': '伦纳德',
    'leo': '利奥',
    'leonardo': '莱昂纳多',
    'lewis': '刘易斯',
    'linda': '琳达',
    'lisa': '丽莎',
    'louis': '路易斯',
    'lucy': '露西',
    'luke': '卢克',
    
    # M
    'madeline': '玛德琳',
    'madison': '麦迪逊',
    'malcolm': '马尔科姆',
    'marc': '马克',
    'marcus': '马库斯',
    'margaret': '玛格丽特',
    'maria': '玛丽亚',
    'marie': '玛丽',
    'mark': '马克',
    'martin': '马丁',
    'mary': '玛丽',
    'mason': '梅森',
    'matthew': '马修',
    'megan': '梅根',
    'melissa': '梅丽莎',
    'michael': '迈克尔',
    'mike': '迈克',
    'michelle': '米歇尔',
    'morgan': '摩根',
    
    # N
    'nancy': '南希',
    'natalie': '娜塔莉',
    'nathan': '内森',
    'nicholas': '尼古拉斯',
    'nick': '尼克',
    'nigel': '奈杰尔',
    'nina': '尼娜',
    'noah': '诺亚',
    'norman': '诺曼',
    
    # O
    'oliver': '奥利弗',
    'olivia': '奥利维亚',
    'oscar': '奥斯卡',
    'owen': '欧文',
    
    # P
    'pamela': '帕梅拉',
    'patricia': '帕特里夏',
    'patrick': '帕特里克',
    'paul': '保罗',
    'peter': '彼得',
    'philip': '菲利普',
    
    # R
    'rachel': '蕾切尔',
    'ralph': '拉尔夫',
    'raymond': '雷蒙德',
    'rebecca': '丽贝卡',
    'richard': '理查德',
    'robert': '罗伯特',
    'robin': '罗宾',
    'roger': '罗杰',
    'ronald': '罗纳德',
    'rose': '罗斯',
    'russell': '拉塞尔',
    'ryan': '瑞恩',
    
    # S
    'sally': '萨莉',
    'sam': '萨姆',
    'samuel': '塞缪尔',
    'sandra': '桑德拉',
    'sara': '萨拉',
    'sarah': '莎拉',
    'scott': '斯科特',
    'sean': '肖恩',
    'sharon': '莎伦',
    'simon': '西蒙',
    'sophia': '索菲亚',
    'stephen': '斯蒂芬',
    'steve': '史蒂夫',
    'steven': '史蒂文',
    'stewart': '斯图尔特',
    'susan': '苏珊',
    
    # T
    'terry': '特里',
    'thomas': '托马斯',
    'tim': '蒂姆',
    'timothy': '蒂莫西',
    'tina': '蒂娜',
    'tom': '汤姆',
    'tommy': '汤米',
    'tony': '托尼',
    'trevor': '特雷弗',
    'tyler': '泰勒',
    
    # U
    'ursula': '厄休拉',
    
    # V
    'victor': '维克多',
    'victoria': '维多利亚',
    'vincent': '文森特',
    'virginia': '弗吉尼亚',
    'vivian': '薇薇安',
    
    # W
    'walter': '沃尔特',
    'warren': '沃伦',
    'wayne': '韦恩',
    'wendy': '温迪',
    'william': '威廉',
    'winston': '温斯顿',
    
    # X
    'xavier': '泽维尔',
    
    # Y
    'yvonne': '伊冯娜',
    
    # Z
    'zachary': '扎卡里',
    'zoe': '佐伊',
}


def normalize_name(name: str) -> str:
    """
    标准化名字
    
    - 转小写
    - 去除空格、标点、特殊字符
    - 统一常见变体（如 "é" -> "e"）
    """
    if not name:
        return ""
    
    # 转小写
    name = name.lower()
    
    # 统一 Unicode 字符
    name = unicodedata.normalize('NFKD', name)
    name = ''.join(c for c in name if not unicodedata.combining(c))
    
    # 只保留字母和数字
    name = re.sub(r'[^a-z0-9]', '', name)
    
    return name


def split_name(name: str) -> Tuple[str, str]:
    """
    分离名字和姓氏
    
    Returns:
        (first_name, last_name)
    """
    parts = name.strip().split()
    if len(parts) >= 2:
        return parts[0].lower(), parts[-1].lower()
    elif len(parts) == 1:
        return parts[0].lower(), ""
    return "", ""


def check_reversed_name(name1: str, name2: str) -> bool:
    """
    检查是否是姓名倒序
    
    如：'frank darabont' vs 'darabont frank'
    """
    parts1 = name1.split()
    parts2 = name2.split()
    
    if len(parts1) == 2 and len(parts2) == 2:
        if parts1[0] == parts2[1] and parts1[1] == parts2[0]:
            return True
    
    return False


def transliterate_name(en_name: str) -> str:
    """
    将英文名音译为中文
    
    Args:
        en_name: 英文名（如 "Tim Robbins"）
        
    Returns:
        中文音译（如 "蒂姆·罗宾斯"）
    """
    if not en_name:
        return ""
    
    parts = en_name.strip().split()
    if not parts:
        return ""
    
    # 音译每个部分
    cn_parts = []
    for part in parts:
        part_lower = part.lower()
        if part_lower in NAME_TRANSLITERATION:
            cn_parts.append(NAME_TRANSLITERATION[part_lower])
        else:
            # 尝试匹配名字的前几个字母
            matched = False
            for key in NAME_TRANSLITERATION:
                if part_lower.startswith(key) or key.startswith(part_lower[:3]):
                    cn_parts.append(NAME_TRANSLITERATION[key])
                    matched = True
                    break
            if not matched:
                cn_parts.append(part)  # 保留原文
    
    return '·'.join(cn_parts) if cn_parts else ""


def match_by_transliteration(tmdb_name_en: str, douban_name_cn: str) -> bool:
    """
    通过音译匹配英文名和中文名
    
    Args:
        tmdb_name_en: TMDB 英文名
        douban_name_cn: 豆瓣中文名
        
    Returns:
        是否匹配
    """
    if not tmdb_name_en or not douban_name_cn:
        return False
    
    # 将英文名音译为中文
    transliterated = transliterate_name(tmdb_name_en)
    
    if not transliterated:
        return False
    
    # 标准化比较
    cn_normalized = re.sub(r'[·\s]', '', douban_name_cn.lower())
    trans_normalized = re.sub(r'[·\s]', '', transliterated.lower())
    
    # 完全匹配
    if cn_normalized == trans_normalized:
        return True
    
    # 包含匹配（处理音译差异）
    if len(cn_normalized) > 3 and len(trans_normalized) > 3:
        # 检查是否有足够的重叠
        common_chars = sum(1 for c in cn_normalized if c in trans_normalized)
        if common_chars >= min(len(cn_normalized), len(trans_normalized)) * 0.7:
            return True
    
    return False


def match_person(tmdb_person: Dict, douban_cast: List[Dict]) -> Optional[Dict]:
    """
    匹配 TMDB 和豆瓣的人物数据
    
    匹配策略（优先级从高到低）：
    1. 英文名精确匹配（不区分大小写）
    2. 英文名模糊匹配（去除空格、标点、特殊字符）
    3. 姓名倒序匹配（如 "Darabont Frank" vs "Frank Darabont"）
    4. 中文名音译匹配
    
    Args:
        tmdb_person: TMDB 人物数据
        douban_cast: 豆瓣演员列表
        
    Returns:
        匹配到的豆瓣人物数据，未匹配返回 None
    """
    tmdb_name = tmdb_person.get('name', '')
    if not tmdb_name:
        return None
    
    tmdb_normalized = normalize_name(tmdb_name)
    tmdb_first, tmdb_last = split_name(tmdb_name)
    
    for douban_person in douban_cast:
        douban_name_en = douban_person.get('nameEn', '')
        douban_name_cn = douban_person.get('name', '')
        
        # 策略1：英文名精确匹配
        if douban_name_en and tmdb_name.lower() == douban_name_en.lower():
            return douban_person
        
        # 策略2：英文名模糊匹配
        if douban_name_en:
            douban_normalized = normalize_name(douban_name_en)
            if tmdb_normalized == douban_normalized:
                return douban_person
        
        # 策略3：姓名倒序匹配
        if douban_name_en:
            douban_first, douban_last = split_name(douban_name_en)
            if tmdb_first and tmdb_last and douban_first and douban_last:
                if tmdb_first == douban_last and tmdb_last == douban_first:
                    return douban_person
        
        # 策略4：中文名音译匹配
        if douban_name_cn and match_by_transliteration(tmdb_name, douban_name_cn):
            return douban_person
    
    return None


def merge_person_data(tmdb_person: Dict, douban_person: Optional[Dict]) -> Dict:
    """
    合并 TMDB 和豆瓣的人物数据
    
    Args:
        tmdb_person: TMDB 人物数据
        douban_person: 豆瓣人物数据（可能为 None）
        
    Returns:
        合并后的人物数据
    """
    tmdb_avatar = None
    if tmdb_person.get('profile_path'):
        tmdb_avatar = f"https://image.tmdb.org/t/p/original{tmdb_person.get('profile_path')}"
    
    douban_avatar = None
    if douban_person and douban_person.get('avatar'):
        douban_avatar = douban_person.get('avatar')
    
    result = {
        'name': None,
        'nameEn': tmdb_person.get('name', ''),
        'character': None,
        'characterEn': tmdb_person.get('character', ''),
        'avatar': tmdb_avatar,
        'tmdbAvatar': tmdb_avatar,
        'doubanAvatar': douban_avatar,
        'tmdbId': tmdb_person.get('id'),
        'doubanId': None,
        'order': tmdb_person.get('order', 0),
    }
    
    if douban_person:
        result['name'] = douban_person.get('name', '')
        result['doubanId'] = douban_person.get('doubanId')
        
        # 角色名：优先豆瓣中文，TMDB 英文
        if douban_person.get('character'):
            result['character'] = douban_person['character']
    
    return result
