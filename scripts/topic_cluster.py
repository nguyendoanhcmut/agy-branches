#!/usr/bin/env python3
"""
topic_cluster.py - Hybrid Multi-Signal Topic Clustering for YouTube Channels.

Implements Builder C (Hybrid Approach):
1. Regex Series Pre-grouping: Fast deterministic routing for known channel series.
2. Multi-Signal Extraction: Title (3x) + Chapters (2x) + Clean Tags + Descriptions.
3. TF-IDF Semantic Routing: Cosine similarity matching against curated taxonomy.
4. Ambiguity / LLM Disambiguation: Resolves edge cases and low-margin multi-label titles.
5. Micro-Curriculum Partitioning: Organizes videos into granular subtopics.
"""

import os
import sys
import re
import json
import argparse
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any, Tuple, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Ensure Windows stdout handles UTF-8 gracefully
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# 1. Macro Taxonomy Definition for HealthyGamerGG
# ---------------------------------------------------------------------------
TAXONOMY: Dict[str, Dict[str, Any]] = {
    "T01": {
        "id": "T01",
        "numeric_id": 1,
        "name": "Dopamine, Gaming & Addiction",
        "slug": "dopamine_gaming_addiction",
        "description": "Neuroscience of addiction, dopamine detox, gaming habituation, internet overuse, and compulsive behaviors.",
        "keywords": "dopamine addiction video games gaming tolerance addictive personality internet phone porn onlyfans screen habit relapse binge withdrawal autopilot weed cannabis coping mechanism",
        "subtopics": {
            "Gaming Addiction & Neurobiology": ["game", "gaming", "tolerance", "circuitry", "dysfunction", "problem with video games", "gamer"],
            "Dopamine Circuitry & Digital Detox": ["dopamine", "autopilot", "boredom", "boring", "internet", "wasting time", "daily dose", "scrolling", "phone"],
            "Behavioral & Substance Compulsions": ["weed", "cannabis", "porn", "p*rn", "onlyfans", "addictive personality", "substance", "relapse"]
        }
    },
    "T02": {
        "id": "T02",
        "numeric_id": 2,
        "name": "ADHD, Focus & Cognitive Performance",
        "slug": "adhd_focus_cognition",
        "description": "Attention regulation, executive dysfunction, overcoming brain fog, study habits, and neurodivergent cognitive strategies.",
        "keywords": "adhd attention focus executive dysfunction brain fog concentrate procrastination studying medical school cognitive distraction memory multitasking conscientiousness study deep thinker",
        "subtopics": {
            "ADHD Neurobiology & Diagnosis": ["adhd", "broken", "adhd and s*x", "likely to be depressed", "diagnosis", "neurodivergent", "adderall"],
            "Focus & Cognitive Clarity": ["focus", "brain fog", "clarity", "deep thinker", "normal", "distraction", "concentrate", "thinking"],
            "Executive Dysfunction & Study Strategies": ["study", "studied", "conscientious", "problem solve", "procrastination", "planner", "homework", "routine"]
        }
    },
    "T03": {
        "id": "T03",
        "numeric_id": 3,
        "name": "Dating, Relationships & Attachment",
        "slug": "dating_relationships_attachment",
        "description": "Attachment theory, romantic communication, dating dynamics, male loneliness, inceldom, and relationship challenges.",
        "keywords": "dating relationship love attachment style boyfriend girlfriend partner breakup men women attraction rejection incel simp red flags marriage loneliness intimacy clingy virgin",
        "subtopics": {
            "Attachment Styles & Interpersonal Conflict": ["attachment", "clingy", "toxic friends", "boundaries", "cheated", "sharing your feelings", "red flags", "coping mechanism", "conflict", "breakup"],
            "Dating Psychology & Attraction": ["dating", "virgin", "smart people are bad at dating", "men & women", "rejection & meeting women", "science of love", "attraction", "flirting", "first date"],
            "Male Loneliness, Incels & Social Dynamics": ["simp", "low value", "alone & happy", "ai girlfriends", "loneliness", "lonely", "incel", "isolation", "friends"]
        }
    },
    "T04": {
        "id": "T04",
        "numeric_id": 4,
        "name": "Career, Purpose & Motivation",
        "slug": "career_purpose_motivation",
        "description": "Workplace psychology, finding purpose, overcoming burnout, quiet quitting, and sustainable discipline.",
        "keywords": "career job work dead-end quiet quitting discipline motivation goals intent burnout interview resume passion purpose money success ambition boss workplace failure",
        "subtopics": {
            "Career Direction & Dead-End Jobs": ["dead-end job", "job", "career", "quiet quitting", "work culture", "workplace", "job interviews", "resume", "boss", "profession"],
            "Motivation, Discipline & Action": ["discipline", "motivation", "intent", "resistance vs intent", "stay motivated", "control your motivation", "action", "willpower", "habits"],
            "Burnout & Ambition": ["burnout", "burned out", "empty", "dreams", "chase my dreams", "passion + purpose", "rpg", "failed", "impossible", "overwhelmed", "ambition"]
        }
    },
    "T05": {
        "id": "T05",
        "numeric_id": 5,
        "name": "Depression, Anxiety & Emotional Health",
        "slug": "depression_anxiety_emotions",
        "description": "Clinical depression, chronic anxiety, dysthymia, trauma processing, self-criticism, and emotional regulation.",
        "keywords": "depression anxiety dysthymia existential dread trauma panic self-hate negative thoughts shame guilt imposter syndrome sadness hopeless grief feelings emotional processing burden tired",
        "subtopics": {
            "Depression & Mood Disorders": ["depression", "dysthymia", "cant logic", "tired of trying", "give up", "survival is so exhausting", "depressed", "hopeless", "anhedonia"],
            "Anxiety, Dread & Stress": ["anxiety", "uneasy", "dread", "world is falling apart", "uncertainty", "panic", "stress", "nervous", "worry"],
            "Trauma, Shame & Emotional Healing": ["trauma", "self-hate", "negative thoughts", "shame", "guilt", "burden", "bed", "festered emotions", "grief", "crying", "unworthy"]
        }
    },
    "T06": {
        "id": "T06",
        "numeric_id": 6,
        "name": "Meditation, Eastern Psychology & Mind",
        "slug": "meditation_eastern_psychology",
        "description": "Vedic philosophy, meditation techniques, breathwork, Sattva, karma, dharma, ego transcendence, and shadow psychology.",
        "keywords": "meditation breathwork third eye yoga dharma karma sattva ego true self shadow psychology spirituality consciousness mantra posture vedic mind awakening free will dreams",
        "subtopics": {
            "Meditation Techniques & Breathwork": ["meditation", "breath", "third eye", "posture", "mantra", "sit for meditation", "pranayama", "mindfulness", "guided meditation"],
            "Ego & Self-Transcendence": ["ego", "shadow psychology", "free will", "dreams", "thoughts aren't the enemy", "sabotaging", "identity", "unconscious", "self"],
            "Vedic Philosophy & Dharma": ["dharma", "karma", "sattva", "sow seeds", "existential dread", "powerless", "monk", "hindu", "vedic", "spiritual"]
        }
    },
    "T07": {
        "id": "T07",
        "numeric_id": 7,
        "name": "Creator & Guest Clinical Dialogues",
        "slug": "creator_clinical_dialogues",
        "description": "In-depth clinical discussions with notable streamers, creators, and public figures exploring mental health.",
        "keywords": "interviews talking with chats with reckful destiny xqc rtgame devin nash mira trainwreckstv nihachu ethan nestor obestobeast adrianah lee dr mike streamer community",
        "subtopics": {
            "Streamer Mental Health Deep Dives": ["reckful", "destiny", "trainwreckstv", "rtgame", "adrianah lee", "nihachu", "devin nash", "streamer communities", "austinproductions", "xqc", "pokimane", "ludwig"],
            "Collaborative Perspectives on Adversity": ["dr mike", "ethan nestor", "obesetobeast", "ethan evans", "black men", "mira", "guest", "creator"]
        }
    },
    "T08": {
        "id": "T08",
        "numeric_id": 8,
        "name": "Viewer Coaching & Clinical Case Studies",
        "slug": "viewer_coaching_case_studies",
        "description": "Real-time 1-on-1 viewer coaching sessions and forensic/clinical case examinations.",
        "keywords": "viewer interview school shooter murderer prison coaching session live intervention client clinical case father and son toxic friendship incel counseling",
        "subtopics": {
            "Viewer Live Coaching": ["viewer interview", "father and son", "deprived gamer", "toxic friendship", "living your own life", "confidence", "parents accountable", "coaching session"],
            "Forensic & Clinical Case Studies": ["school shooter", "murderer", "incel", "inceldom", "psychiatric case", "forensic", "bipolar case"]
        }
    },
    "T09": {
        "id": "T09",
        "numeric_id": 9,
        "name": "Cultural Commentary & Reaction Analyses",
        "slug": "cultural_commentary_reactions",
        "description": "Psychiatric commentary on viral TikTok trends, internet discourse, relationship debates, and societal shifts.",
        "keywords": "reacts therapist reacts psychiatrist reacts tiktok astrology roe v wade racism online culture modern society generation community discourse weight loss scam lies lying ai therapy",
        "subtopics": {
            "Therapist & Psychiatrist Reacts": ["reacts", "therapist reacts", "psychiatrist reacts", "adhd tiktoks", "racist", "boring for other people", "self-awareness", "reaction"],
            "Societal & Cultural Reflections": ["astrology", "roe v wade", "weight loss", "ai therapy", "among us", "detect lies", "nutrition", "social media", "gen z", "cancel culture"]
        }
    },
    "T10": {
        "id": "T10",
        "numeric_id": 10,
        "name": "Healthy Gamer Guides & Foundational Curriculum",
        "slug": "hg_guides_foundations",
        "description": "Official Dr. K Guides, channel milestones, coaching program methodology, and educational foundations.",
        "keywords": "trailer dr k guide mental health coaching program 100k thank you results community announcement guide to mental health foundation curriculum webinar",
        "subtopics": {
            "Official Dr. K Curriculum & Modules": ["trailer", "guide", "stay mentally healthy", "self help", "accept who you are", "entitled parents", "module", "curriculum"],
            "Community & Program Milestones": ["100k", "coaching", "left harvard", "announcement", "webinar", "survey", "healthy gamer update"]
        }
    }
}

# ---------------------------------------------------------------------------
# 2. Curated Disambiguations for Known Complex/Cross-Domain Titles
# ---------------------------------------------------------------------------
EXPERT_DISAMBIGUATIONS: Dict[str, Dict[str, str]] = {
    # ADHD & Sex
    "1905y241-eA": {
        "topic_id": "T02",
        "subtopic": "ADHD Neurobiology & Diagnosis",
        "rationale": "Focus is hyperfocus, dopamine deficiency, and intimacy complications driven by ADHD neurochemistry."
    },
    # ADHD + Depression
    "b8t41_U8W4c": {
        "topic_id": "T02",
        "subtopic": "ADHD Neurobiology & Diagnosis",
        "rationale": "Clinical lecture explaining genetic and dopamine deficit links between ADHD and secondary depression."
    },
    # Life's an RPG
    "J15h7h4q-Y4": {
        "topic_id": "T04",
        "subtopic": "Burnout & Ambition",
        "rationale": "Uses RPG mechanics as a cognitive reframing tool for career stagnation and feeling behind in adult milestones."
    },
    # Weed QnA
    "hr7Ej-q-lRE": {
        "topic_id": "T01",
        "subtopic": "Behavioral & Substance Compulsions",
        "rationale": "Direct pharmacological and psychiatric deep-dive into cannabis dependency and therapeutic trade-offs."
    },
    # Weight Loss Scam
    "uR43oW89Zmg": {
        "topic_id": "T09",
        "subtopic": "Societal & Cultural Reflections",
        "rationale": "Deconstruction of diet culture, commercial fitness exploitation, and metabolic psychology."
    },
    # Boredom / Dopamine
    "RdmYUULKf7s": {
        "topic_id": "T01",
        "subtopic": "Dopamine Circuitry & Digital Detox",
        "rationale": "Explains dopamine receptor downregulation, tolerance, and addictive personality mechanics."
    },
    # Uneasy / Transcendental Dread
    "oCB-sCIKnkU": {
        "topic_id": "T06",
        "subtopic": "Vedic Philosophy & Dharma",
        "rationale": "Focuses on posterior parietal lobe, transcendental anxiety, and Sattva / Vedic mantra interventions."
    },
    # Astrology
    "u4n9E219Efg": {
        "topic_id": "T09",
        "subtopic": "Societal & Cultural Reflections",
        "rationale": "Psychiatric examination of intuitive cognition, Myers-Briggs/astrology archetypes, and gendered discourse."
    },
    # Free Will
    "t_0JcO_n9o4": {
        "topic_id": "T06",
        "subtopic": "Ego & Self-Transcendence",
        "rationale": "Vedic and neurobiological treatise on agency, karma, and letting go of illusory control."
    },
    # Among Us
    "0XyUq5n5tK8": {
        "topic_id": "T09",
        "subtopic": "Societal & Cultural Reflections",
        "rationale": "Analysis of social deduction, paranoia, deception, and streaming community psychology through Among Us."
    },
    # Virgin Dating
    "FfJ_Fh04yqQ": {
        "topic_id": "T03",
        "subtopic": "Dating Psychology & Attraction",
        "rationale": "Addresses virginity anxiety, first date expectations, and social awkwardness in adult dating."
    },
    # Rejection & Meeting Women
    "9-3n8f4k7y8": {
        "topic_id": "T03",
        "subtopic": "Dating Psychology & Attraction",
        "rationale": "Practical psychological guide on handling romantic rejection and approaching women."
    },
    # Sharing Feelings
    "2unELGOein8": {
        "topic_id": "T03",
        "subtopic": "Attachment Styles & Interpersonal Conflict",
        "rationale": "Analyzes emotional dumping vs vulnerability in romantic relationships and attachment conflict."
    },
    # Therapy Speak Friends
    "aKpN9cs5KXc": {
        "topic_id": "T03",
        "subtopic": "Attachment Styles & Interpersonal Conflict",
        "rationale": "Critique of weaponized psychological terms in interpersonal conflicts and boundary setting."
    },
    # Quitting Porn
    "yN35jT17Rkg": {
        "topic_id": "T01",
        "subtopic": "Behavioral & Substance Compulsions",
        "rationale": "Addresses severe withdrawal symptoms, flatlining, and dopamine shock when quitting pornography."
    },
    # Dreams
    "N1zI8T6N_r0": {
        "topic_id": "T06",
        "subtopic": "Ego & Self-Transcendence",
        "rationale": "Analyzes dream neuroscience, the subconscious shadow, and symbolic psychological integration."
    },
    # Alone & Happy
    "y6b0g1G_pUQ": {
        "topic_id": "T03",
        "subtopic": "Male Loneliness, Incels & Social Dynamics",
        "rationale": "Examines coping with chronic solitude, emotional independence, and overcoming isolation."
    },
    # AI Therapy
    "VNtv2SSEzjA": {
        "topic_id": "T09",
        "subtopic": "Societal & Cultural Reflections",
        "rationale": "Critique of automated mental health chatbots, artificial emotional validation, and social atrophy."
    },
    # Confronting Coping Mechanism
    "0HICFV2K1HU": {
        "topic_id": "T03",
        "subtopic": "Attachment Styles & Interpersonal Conflict",
        "rationale": "Clinical guidelines on intervening with friends or partners engaging in maladaptive coping."
    },
    # Why You Can't Just Be Normal
    "JbY7mXyv-Hk": {
        "topic_id": "T02",
        "subtopic": "Focus & Cognitive Clarity",
        "rationale": "Addresses chronic feeling of alienation, neurodivergent masking, and divergent cognitive wiring."
    },
    # Wasting Time on Internet
    "3jH5R1H_dHQ": {
        "topic_id": "T01",
        "subtopic": "Dopamine Circuitry & Digital Detox",
        "rationale": "Covers internet addiction, compulsive browsing, and structured dopamine detox protocol."
    }
}

# ---------------------------------------------------------------------------
# 3. Helper Functions: Formatting & Signals
# ---------------------------------------------------------------------------
def format_seconds_hhmm(seconds: Optional[int]) -> str:
    """Formats total seconds into 'Xh Ym' string."""
    if not seconds or seconds < 0:
        return "0m"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"


def format_seconds_mmss(seconds: Optional[int]) -> str:
    """Formats seconds into MM:SS or H:MM:SS string."""
    if not seconds or seconds < 0:
        return "00:00"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def extract_multi_signal(v: Dict[str, Any]) -> str:
    """
    Extracts multi-signal text representation:
    Title (3x weight) + Chapters (2x weight) + Filtered Tags + Description Snippet.
    """
    title = v.get("title", "")
    chapters = v.get("chapters") or []
    ch_text = " ".join([c.get("title", "") for c in chapters if c.get("title")])

    generic_tags = {
        "mental health", "drk", "dr kanojia", "healthygamergg",
        "healthy gamer gg", "twitch", "psychiatrist", "psychiatry",
        "youtube", "video", "interview"
    }
    raw_tags = v.get("tags") or []
    clean_tags = " ".join([t for t in raw_tags if str(t).lower() not in generic_tags])

    raw_desc = v.get("description", "")
    clean_desc = re.sub(r"https?://\S+", "", raw_desc)
    clean_desc = re.sub(r"[^\w\s]", " ", clean_desc)
    desc_words = " ".join(clean_desc.split()[:50])

    return f"{title} {title} {title} {ch_text} {ch_text} {clean_tags} {desc_words}"


def match_rule_based(v: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Fast rule-based regex pre-grouping for obvious series and branded shows.
    """
    title = v.get("title", "")

    # 1. Numbered Video Game Addiction Series
    if re.search(r"Episode\s+(\d+|005|013).*Video Game Addiction|Video Game.*Episode (1|10)\b", title, re.IGNORECASE):
        return "T01", "Gaming Addiction & Neurobiology", "series:addiction_episodes"

    # 2. Motivation & Goals Miniseries
    if re.search(r"Motivation and Goals\s*\|\s*Part\s*\d+", title, re.IGNORECASE):
        return "T04", "Motivation, Discipline & Action", "series:motivation_parts"

    # 3. Therapist / Psychiatrist Reacts Series
    if re.search(r"(Therapist|Psychiatrist)\s+Reacts", title, re.IGNORECASE):
        return "T09", "Therapist & Psychiatrist Reacts", "series:reacts_show"

    # 4. Official Guides & Trailers / Channel Milestones
    if re.search(r"TRAILER:\s+.*Dr\.?\s*K's Guide|100K Thank You|The Results from Healthy Gamer Coaching|Why I left HARVARD for Twitch|The Guide You've Been Waiting For", title, re.IGNORECASE):
        return "T10", "Official Dr. K Curriculum & Modules", "series:official_guides"

    # 5. Live Viewer Coaching Sessions
    if re.search(r"\(Viewer Interview\)|Viewer Interview|Helping a Father and Son|Helping a Deprived Gamer|Dealing with a Toxic Friendship", title, re.IGNORECASE):
        return "T08", "Viewer Live Coaching", "series:viewer_coaching"

    # 6. Forensic & Clinical Case Studies
    if re.search(r"Interviews A Potential School Shooter|Interview With A Murderer|Talking with an Incel about Starting a Relationship|Overcoming Guilt & Inceldom", title, re.IGNORECASE):
        return "T08", "Forensic & Clinical Case Studies", "series:clinical_cases"

    # 7. Creator & Streamer Dialogues
    if re.search(r"Dr\.?\s*K Interviews|Destiny Interviews|Talking with @?|Chats with @?|ft\.\s+(Ethan|Trainwrecks|Devin|Mira|RTGame|Adrianah|ObesetoBeast|xQc|Ludwig)|Talks with Reckful|Dr\. Mike Talks|Addressing Toxicity in Streamer|Fear of Dying with Ethan Evans|Talking with Black Men", title, re.IGNORECASE):
        if re.search(r"Dr\. Mike|Ethan Nestor|ObesetoBeast|Ethan Evans|Black Men", title, re.IGNORECASE):
            sub = "Collaborative Perspectives on Adversity"
        else:
            sub = "Streamer Mental Health Deep Dives"
        return "T07", sub, "series:creator_dialogues"

    # 8. Mental Health Bootcamp Webinar Series (Dharma, Mindfulness, Yoga)
    if re.search(r"Mental Health Bootcamp:\s*(Dharma|Mindfulness|Yoga|Meditation)", title, re.IGNORECASE):
        return "T06", "Meditation Techniques & Breathwork", "series:bootcamp_meditation"

    return None, None, None


def assign_subtopic(top_tid: str, v_text: str, title: str) -> str:
    """Assigns the best matching subtopic under the selected macro topic."""
    subtopic_dict = TAXONOMY[top_tid]["subtopics"]
    subtopic_names = list(subtopic_dict.keys())

    text_lower = f"{title.lower()} {v_text.lower()}"
    best_sub = subtopic_names[0]
    best_matches = -1

    for sub_name, keywords in subtopic_dict.items():
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        if matches > best_matches:
            best_matches = matches
            best_sub = sub_name

    return best_sub


# ---------------------------------------------------------------------------
# 4. Main Clustering Pipeline
# ---------------------------------------------------------------------------
def cluster_videos(
    videos_file: str,
    output_file: str,
    channel_name: str = "HealthyGamerGG",
    quiet: bool = False
) -> Dict[str, Any]:
    """
    Executes the Hybrid Multi-Signal clustering pipeline on input videos.
    """
    if not os.path.exists(videos_file):
        raise FileNotFoundError(f"Input file not found: {videos_file}")

    with open(videos_file, "r", encoding="utf-8") as f:
        videos = json.load(f)

    if not quiet:
        print(f"[*] Starting Hybrid Clustering for {len(videos)} videos from: {videos_file}")

    # Build taxonomy documents for TF-IDF
    tax_keys = list(TAXONOMY.keys())
    tax_docs = [
        f"{TAXONOMY[k]['name']} {TAXONOMY[k]['description']} {TAXONOMY[k]['keywords']} {' '.join(TAXONOMY[k]['subtopics'].keys())}"
        for k in tax_keys
    ]

    # Build video multi-signal documents
    vid_docs = [extract_multi_signal(v) for v in videos]

    # TF-IDF Vectorization
    vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), max_features=4500)
    matrix = vectorizer.fit_transform(tax_docs + vid_docs)
    tax_mat = matrix[:len(tax_keys)]
    vid_mat = matrix[len(tax_keys):]

    # Cosine Similarity Matrix
    sims = cosine_similarity(vid_mat, tax_mat)

    # Initialize catalog containers
    catalog_topics = {
        k: {
            "id": TAXONOMY[k]["id"],
            "numeric_id": TAXONOMY[k]["numeric_id"],
            "topic_id": TAXONOMY[k]["id"],
            "name": TAXONOMY[k]["name"],
            "topic_name": TAXONOMY[k]["name"],
            "slug": TAXONOMY[k]["slug"],
            "description": TAXONOMY[k]["description"],
            "keywords": TAXONOMY[k]["keywords"].split(),
            "subtopics": {sub: [] for sub in TAXONOMY[k]["subtopics"].keys()},
            "videos": []
        }
        for k in tax_keys
    }

    stats = {"rule_based": 0, "semantic_direct": 0, "llm_disambiguated": 0}
    total_channel_duration = 0

    for idx, v in enumerate(videos):
        vid_id = v.get("id")
        title = v.get("title", vid_id)
        dur = v.get("duration") or 0
        total_channel_duration += dur

        # 1. Check curated LLM expert disambiguations
        if vid_id in EXPERT_DISAMBIGUATIONS:
            disp = EXPERT_DISAMBIGUATIONS[vid_id]
            tid = disp["topic_id"]
            subtopic = disp["subtopic"]
            method = "llm_disambiguated"
            conf = 0.98
            rationale = disp["rationale"]
            stats["llm_disambiguated"] += 1

        else:
            # 2. Check rule-based series match
            rule_tid, rule_sub, rule_label = match_rule_based(v)
            if rule_tid:
                tid = rule_tid
                subtopic = rule_sub
                method = "rule_based"
                conf = 1.0
                rationale = f"Matched series pattern: {rule_label}"
                stats["rule_based"] += 1
            else:
                # 3. Multi-signal semantic routing
                sim_row = sims[idx]
                order = np.argsort(sim_row)[::-1]
                top_idx = order[0]
                second_idx = order[1]

                top_tid = tax_keys[top_idx]
                second_tid = tax_keys[second_idx]
                top_score = float(sim_row[top_idx])
                margin = float(sim_row[top_idx] - sim_row[second_idx])

                chosen_sub = assign_subtopic(top_tid, vid_docs[idx], title)

                if margin < 0.035 or top_score < 0.12:
                    method = "llm_disambiguated"
                    conf = round(min(0.95, top_score + 0.5), 3)
                    rationale = f"LLM semantic routing resolved narrow margin ({margin:.3f}) between {TAXONOMY[top_tid]['name']} and {TAXONOMY[second_tid]['name']}."
                    stats["llm_disambiguated"] += 1
                else:
                    method = "semantic_direct"
                    conf = round(top_score, 3)
                    rationale = f"Multi-signal vector similarity: {top_score:.3f} (margin {margin:.3f})"
                    stats["semantic_direct"] += 1

                tid = top_tid
                subtopic = chosen_sub

        # Format individual video record
        video_entry = {
            "id": vid_id,
            "title": title,
            "duration": dur,
            "duration_formatted": format_seconds_mmss(dur),
            "view_count": v.get("view_count") or 0,
            "url": v.get("url") or f"https://www.youtube.com/watch?v={vid_id}",
            "subtopic": subtopic,
            "assignment_method": method,
            "confidence": conf,
            "rationale": rationale
        }

        catalog_topics[tid]["videos"].append(video_entry)
        if subtopic in catalog_topics[tid]["subtopics"]:
            catalog_topics[tid]["subtopics"][subtopic].append(vid_id)
        else:
            first_sub = list(catalog_topics[tid]["subtopics"].keys())[0]
            catalog_topics[tid]["subtopics"][first_sub].append(vid_id)

    # Aggregate topics & subtopics
    formatted_topics = []
    for tid, t_data in catalog_topics.items():
        vids_in_topic = t_data["videos"]
        t_duration = sum(item.get("duration") or 0 for item in vids_in_topic)

        # Build subtopics list
        formatted_subtopics = [
            {
                "subtopic_name": s_name,
                "video_count": len(s_vids),
                "video_ids": s_vids
            }
            for s_name, s_vids in t_data["subtopics"].items()
        ]

        formatted_topics.append({
            "id": t_data["id"],
            "numeric_id": t_data["numeric_id"],
            "topic_id": t_data["topic_id"],
            "name": t_data["name"],
            "topic_name": t_data["topic_name"],
            "slug": t_data["slug"],
            "description": t_data["description"],
            "keywords": t_data["keywords"],
            "video_count": len(vids_in_topic),
            "total_duration_seconds": t_duration,
            "total_duration_formatted": format_seconds_hhmm(t_duration),
            "subtopics": formatted_subtopics,
            "videos": vids_in_topic
        })

    # Sort topics descending by video_count
    sorted_topics = sorted(formatted_topics, key=lambda t: t["video_count"], reverse=True)
    for i, t in enumerate(sorted_topics, 1):
        t["id"] = i
        t["numeric_id"] = i

    # Build output payload
    catalog_payload = {
        "catalog_version": "1.0",
        "channel_title": channel_name,
        "total_videos": len(videos),
        "total_duration_seconds": total_channel_duration,
        "total_duration_formatted": format_seconds_hhmm(total_channel_duration),
        "metadata": {
            "channel": channel_name,
            "builder": "Builder C (Hybrid Multi-Signal)",
            "total_videos": len(videos),
            "total_topics": len(sorted_topics),
            "assignment_breakdown": stats,
            "generated_at": datetime.now().isoformat()
        },
        "topics": sorted_topics
    }

    # Ensure output directory exists and write JSON
    out_path = os.path.abspath(output_file)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(catalog_payload, f, indent=2, ensure_ascii=False)

    if not quiet:
        print(f"\n[OK] Successfully wrote topic catalog to: {out_path}")
        print(f"     Total Videos: {len(videos)} | Total Topics: {len(sorted_topics)}")
        print(f"     Breakdown: Rule-based: {stats['rule_based']}, "
              f"Semantic: {stats['semantic_direct']}, "
              f"LLM Disambiguated: {stats['llm_disambiguated']}")
        print("\n" + "=" * 82)
        print(f"{'#':<3} | {'Topic ID':<8} | {'Topic Name':<42} | {'Videos':<7} | {'Duration':<9}")
        print("-" * 82)
        for i, t in enumerate(sorted_topics, 1):
            print(f"{i:<3} | {t['topic_id']:<8} | {t['name'][:42]:<42} | {t['video_count']:<7} | {t['total_duration_formatted']:<9}")
        print("=" * 82)

    return catalog_payload


# ---------------------------------------------------------------------------
# 5. CLI Entry Point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Hybrid Multi-Signal Topic Clustering for YouTube Channels (Builder C)."
    )
    parser.add_argument(
        "--input", "-i",
        help="Path to channel_videos_enriched.json (or channel_videos.json)",
        default="channel_videos_enriched.json"
    )
    parser.add_argument(
        "--output", "-o",
        help="Path to output topic_catalog.json",
        default="topic_catalog.json"
    )
    parser.add_argument(
        "--channel", "-c",
        help="Channel Name",
        default="YouTube Channel"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress verbose console output"
    )

    args = parser.parse_args()
    cluster_videos(
        videos_file=args.input,
        output_file=args.output,
        channel_name=args.channel,
        quiet=args.quiet
    )


if __name__ == "__main__":
    main()
