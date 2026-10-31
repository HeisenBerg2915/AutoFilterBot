import re

# =========================
# UNWANTED TAGS
# =========================

TAGS = [
    "dvdwap.com", "Dvdworld", "DVDWORLD", "DVDWO",
    "@ALBCINEMAS©", "@FC_HEVC", "[CF]", "KC", "KC_",
    "MF", "themoviesboss", "MLM", "MZone", "MoviezzClub",
    "HDMVCOUNTER", "YMovieZNew", "A2MOVIES",
    "HDTCPREDVDFILES", "Tamil_Full_Movie",

    "@ADrama_Lovers", "@AVA", "@BuLLMovieee", "@BM_Links",
    "@BestMovie", "@T4TSA", "@CC", "@CC_All",
    "@CC_ALL_MOVIES2", "@CC_NEW", "@CC_X265",
    "@CCineClub", "@CCM", "@CMVLA", "@CE_Links",
    "@CMEHD", "@Clipmate_Movie_Team", "@CR_Rockers",
    "@cinecom88", "@Cinematic_world", "@Cinema Company",
    "@cinema_company", "@Cinema_Company",
    "@CINEMA_BUDDIES", "@Country_Fellows",
    "@Cinema_Kottaka", "@cinema library", "@CKMovies",
    "@CK_HEVC", "@CK_Moviez", "CT™️",
    "@CelluloidCineClub", "@colorkannadi_movies",
    "@C_V", "@CVM", "@DailyMovieZhunt", "@desimovies",
    "@DK_Drama", "@DM_LinkZzzz", "@DMovies",
    "@DramaOST", "@Dubbedmovies", "@DVDWOALL",
    "@DvdWap", "@E4E", "@E4E_Rockers",
    "Filmy4wap_xyz", "@FBM_x265", "@FBM_HW",
    "@FBM_New", "@FILIMHOUSE", "@FilmCage",
    "@Film_Kottaka", "@FrediesChannel",
    "@HEVC_Cinemaz", "@IM", "@HEVC_Moviesz",
    "@HOREK_ROKOM", "@HEVCHubX", "@Hk",
    "@IndianMoviez", "@KBO", "@KD_Deck", "@KGRockers",
    "@KW", "@KR", "@KannadaWarriors",
    "@KeralaBoxOffice", "@KL_ROCKERZ",
    "@lonelylinkss", "@Links2U", "@Linkz_MM", "@ᒪᕈT",

    "@M_Zone", "@mobile_mm", "Malayalam_Full_Movie",
    "@Mallu_Movies", "@malayalam movies", "@MAASFILE",
    "@MC", "@MC_4U", "@MinaKaze", "@MJ_Linkz",
    "@MJ_Moviez", "@MM", "@MM_Movies", "@MM_Linkz",
    "@MM_NEW", "@MM_ALL", "@MM_TvSeries",
    "@MOVIEHUNT", "@MOVIEZMOB", "@MPC",
    "@MalluRockers", "@Mallu_Rockers", "@mfmixsouth",
    "@Mc_South", "@MovieWorld2000", "@Movie_Hub",
    "@N3SSSS", "@bheeshmat", "@desimovies Telegram",
    "@favio", "@film_down_load", "@iMediaShare",
    "@infotainmentmedia", "@kickass_torrents", "@msp",
    "@moviescollection17", "@moviesdeveloper",
    "@MoviesTop10", "@MoviesWar", "@myflixx",
    "@NithinMovies", "@NRDramaa", "@nanacinemas",
    "@OB", "PDisk", "@PIT", "@PM", "@PM_Old",
    "@Qualitymovies", "@Rarefilms.", "@R_A_R_B_G",
    "@RickyChannel", "@RatedRMovies", "@Sky_MoviesHD",
    "@sherlibrary", "@SY_MS", "@telugu_moviez",
    "@TG UPDATES1", "@TN60_LinkzZ", "@TEAMxKL",
    "@TV 30NAMA1", "@TamilPrime_LinkZz",
    "@TamilDubbs", "@TamilMV", "@TGmovie9",
    "@TamilMV_Live", "@TamilRockers", "@Tamilmoviez",
    "@Tamil_HD_Movies_Requests", "@Tamil_Linkz",
    "Tamil_LinkZz", "@Tamil_LinkzZ", "@Tamil_Seriesz",
    "@TeamHDT", "@Team_HDT", "@Team_Hevc",
    "@Theprofffesorr", "@TR_Moviez", "@TR_Updates",
    "@Tv2Us", "@TvSeriesBay", "@UCDump", "@VR",
    "www_Movcr_cc", "@WMR", "@WorldCinemaToday",
    "@X265 E4E", "@YTSLT", "@cinemaheist",
    "@trolldcompany", "@yamandanmovies",
    "@Zee_Keralam_HD", "F&T", "@ALBCINEMASALL",

    # =========================
    # WEBSITE TAGS
    # =========================

    "www.",
    "www_DVDWap_Com_",
    "www_TamilMV_pw",
    "www_1TamilMV",
    "www_1TamilMV_fun",
    "www_1TamilMV_rodeo",
    "www_1TamilMV_fans",
    "www_1TamilMV_nl",
    "www_1TamilMV_art",
    "www_1TamilMV_org",
    "www_1TamilMV_eu",
    "www_1TamilMV_men",
    "www_1TamilMV_wtf",
    "www_1TamilMV_city",
    "www_1TamilMV_cafe",
    "www_1TamilMV_help",
    "www_1TamilMV_im",
    "www_1TamilMV_phd",
    "www_1TamilMV_one",
    "www_1TamilMV_guru",
    "www_1TamilMV_us",
    "www_1TamilMV_live",
    "www_1TamilMV_pw",
    "www_1TamilMV_life",
    "www_1TamilMV_me",
    "www_1TamilMV_vin",
    "www_1TamilMV_sbs",
    "www_1TamilMV_mx",
    "www_1TamilMV_team",
    "www_1TamilMV_cyou",
    "www_1TamilMV_pics",
    "www_1TamilMV_click",
    "www_1TamilMV_pro",
    "www_1TamilMV_lease",
    "www_1TamilMV_rocks",
    "www_1TamilMV_meme",
    "www_1TamilMV_ing",
    "www_1TamilMV_pizza",
    "www_1TamilMV_li",
    "www_1TamilMV_top",
    "www_1TamilMV_promo",
    "www_1TamilMV_gs",
    "www_1TamilMV_bio",
    "www_1TamilMV_xyz",

    # =========================
    # 1TAMILMV DOMAINS
    # =========================

    "www.1TamilBlasters.dad",
    "www.1TamilMV.ac",
    "www.1TamilMV.cafe",
    "www.1TamilMV.eu",
    "www.1TamilMV.fans",
    "www.1TamilMV.fun",
    "www.1TamilMV.gold",
    "www.1TamilMV.gs",
    "www.1TamilMV.help",
    "www.1TamilMV.im",
    "www.1TamilMV.ing",
    "www.1TamilMV.lease",
    "www.1TamilMV.li",
    "www.1TamilMV.life",
    "www.1TamilMV.me",
    "www.1TamilMV.men",
    "www.1TamilMV.meme",
    "www.1TamilMV.mx",
    "www.1TamilMV.nl",
    "www.1TamilMV.one",
    "www.1TamilMV.org",
    "www.1TamilMV.phd",
    "www.1TamilMV.pics",
    "www.1TamilMV.pizza",
    "www.1TamilMV.pro",
    "www.1TamilMV.prof",
    "www.1TamilMV.promo",
    "www.1TamilMV.pw",
    "www.1TamilMV.rodeo",
    "www.1TamilMV.rocks",
    "www.1TamilMV.sbs",
    "www.1TamilMV.team",
    "www.1TamilMV.top",
    "www.1TamilMV.us",
    "www.1TamilMV.vin",
    "www.1TamilMV.wf",
    "www.1TamilMV.wtf",
    "www.1TamilMV.xyz",
    "www.1TamilMV.bio",

    "@mfmixsouth",
]


# =========================
# CLEAN FILE NAME
# =========================

def clean_file_name(file_name):

    if not file_name:
        return "Unknown File"

    cleaned = str(file_name)

    for tag in sorted(TAGS, key=len, reverse=True):

        tag = tag.strip()

        if not tag:
            continue

        pattern = (
            r"(?<![A-Za-z0-9])"
            + re.escape(tag)
            + r"(?![A-Za-z0-9])"
        )

        cleaned = re.sub(
            pattern,
            " ",
            cleaned,
            flags=re.IGNORECASE
        )

    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned
    ).strip()

    cleaned = re.sub(
        r"^[\W_]+|[\W_]+$",
        "",
        cleaned
    ).strip()

    return cleaned or "Unknown File"
