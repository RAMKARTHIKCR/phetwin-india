
import pandas as pd

CSV_PATH = "data/foods_final.csv"

tamil_names = {
    "Black amaranth seed": "கருப்பு அமராந்த் விதை",
    "Amaranth seed, pale brown": "வெளிர் பழுப்பு அமராந்த் விதை",
    "Bajra (pearl millet)": "கம்பு",
    "Barley": "பார்லி",
    "Jowar (sorghum)": "சோளம்",
    "Maize, dry": "உலர்ந்த மக்காச்சோளம்",
    "Maize, tender, local": "இளம் உள்ளூர் மக்காச்சோளம்",
    "Maize, tender, sweet": "இளம் இனிப்பு மக்காச்சோளம்",
    "Quinoa": "கினோவா",
    "Ragi (finger millet)": "கேழ்வரகு",
    "Rice flakes": "அவல்",
    "Rice puffed": "பொரி",
    "Rice, raw, brown": "தீட்டாத பழுப்பு அரிசி",
    "Rice, parboiled, milled": "தீட்டிய புழுங்கல் அரிசி",
    "Rice, raw, milled": "தீட்டிய பச்சரிசி",
    "Samai (little millet)": "சாமை",
    "Varagu (kodo millet)": "வரகு",
    "Wheat flour, refined": "மைதா மாவு",
    "Wheat flour, atta": "கோதுமை மாவு",
    "Wheat, whole": "முழுக் கோதுமை",
    "Wheat, bulgur": "உடைத்த கோதுமை",
    "Wheat, semolina": "ரவை",
    "Wheat, vermicelli": "சேமியா",
    "Wheat, vermicelli, roasted": "வறுத்த சேமியா",

    "Bengal gram, dal": "கடலைப் பருப்பு",
    "Bengal gram, whole": "கொண்டைக்கடலை",
    "Black gram, dal": "உளுத்தம் பருப்பு",
    "Black gram, whole": "முழு உளுந்து",
    "Cowpea, brown": "பழுப்பு காராமணி",
    "Cowpea, white": "வெள்ளை காராமணி",
    "Field bean, black": "கருப்பு மொச்சை",
    "Field bean, brown": "பழுப்பு மொச்சை",
    "Field bean, white": "வெள்ளை மொச்சை",
    "Green gram, dal": "பாசிப்பருப்பு",
    "Green gram, whole": "பச்சைப்பயறு",
    "Horse gram, whole": "கொள்ளு",
    "Lentil dal": "மசூர் பருப்பு",
    "Lentil whole, brown": "பழுப்பு முழு மசூர் பருப்பு",
    "Lentil whole, yellowish": "மஞ்சள் நிற முழு மசூர் பருப்பு",
    "Peas, dry": "உலர்ந்த பட்டாணி",
    "Red gram, dal": "துவரம் பருப்பு",
    "Moth bean": "மொத் பயறு",
    "Rajmah, black": "கருப்பு ராஜ்மா",
    "Rajmah, brown": "பழுப்பு ராஜ்மா",
    "Rajmah, red": "சிவப்பு ராஜ்மா",
    "Red gram, whole": "முழு துவரை",
    "Ricebean": "அரிசிப்பயறு",
    "Soybean, brown": "பழுப்பு சோயாபீன்",
    "Soybean, white": "வெள்ளை சோயாபீன்",
}

df = pd.read_csv(CSV_PATH)

# Check that every English food has a translation.
missing = set(df["name_en"]) - set(tamil_names)

if missing:
    raise ValueError(f"Missing Tamil translations: {sorted(missing)}")

# Preserve existing nutrient and source data.
original_nutrients = df[
    ["protein_g_per_100g", "phe_mg_per_100g"]
].copy()

df["name_ta"] = df["name_en"].map(tamil_names)

# Verify nutrient values were not changed.
assert df[
    ["protein_g_per_100g", "phe_mg_per_100g"]
].equals(original_nutrients)

df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

print("Tamil food names updated successfully!")
print("Total foods:", len(df))
print("Tamil names populated:", df["name_ta"].notna().sum())
print("Missing Tamil names:", df["name_ta"].isna().sum())
print("\nPreview:")
print(df[["name_en", "name_ta"]].to_string(index=False))
