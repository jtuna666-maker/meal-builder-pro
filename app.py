import streamlit as st
import random
import json
import os
import easyocr
import numpy as np
from PIL import Image

st.set_page_config(page_title="Meal Builder Pro", layout="wide", page_icon="🍳")
IMAGE_DIR = "recipe_images"
DATA_FILE = "meal_data.json"

if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def get_reader():
    return easyocr.Reader(['en'])

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return None
    return None

def save_data():
    data = {"library": st.session_state.library, "plan": st.session_state.plan}
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

saved_data = load_data()

if 'library' not in st.session_state:
    raw_library = saved_data["library"] if saved_data else {}
    # --- FIX: Convert old list-style recipes to new dictionary-style ---
    processed_library = {}
    for name, info in raw_library.items():
        if isinstance(info, list):
            processed_library[name] = {"ingredients": info, "category": "Other", "image": None}
        else:
            processed_library[name] = info
    
    st.session_state.library = processed_library if processed_library else {
        "Sloppy Joes": {"ingredients": ["Ground Beef", "Buns"], "category": "Dinner", "image": None}
    }

if 'plan' not in st.session_state:
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    if saved_data and "plan" in saved_data:
        st.session_state.plan = saved_data["plan"]
    else:
        st.session_state.plan = {f"Week {w}": {d: "" for d in days} for w in range(1, 5)}

st.title("👨‍🍳 Meal Builder Pro")
st.caption("v2.1 - Fixed & Final")

tab1, tab2, tab3 = st.tabs(["🗓️ Planning Grid", "🛒 Grocery List", "📚 Recipe Library"])

with tab1:
    view_mode = st.radio("View Mode", ["Weekly", "Monthly"], horizontal=True)
    col1, col2 = st.columns([1, 3])

    with col1:
        st.subheader("🛠️ Controls")
        categories = ["All"] + sorted(list(set(v.get('category', 'Other') for v in st.session_state.library.values())))
        cat_filter = st.selectbox("Filter by Category:", categories)
        
        filtered_meals = [name for name, info in st.session_state.library.items() 
                         if cat_filter == "All" or info.get('category') == cat_filter]
        
        selected_meal = st.selectbox("Pick a meal:", sorted(filtered_meals))
        
        c1, c2 = st.columns(2)
        with c1: target_week = st.selectbox("Week:", list(st.session_state.plan.keys()))
        with c2: target_day = st.selectbox("Day:", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
        
        if st.button("📍 Add to Plan", use_container_width=True):
            st.session_state.plan[target_week][target_day] = selected_meal
            save_data()
            st.toast(f"Added {selected_meal}!")

        st.divider()
        if st.button("🔀 Shuffle Everything", use_container_width=True):
            meals_list = list(st.session_state.library.keys())
            if meals_list:
                for week in st.session_state.plan:
                    for day in st.session_state.plan[week]:
                        st.session_state.plan[week][day] = random.choice(meals_list)
                save_data()
                st.rerun()

    with col2:
        if view_mode == "Weekly":
            st.subheader(f"📅 Schedule: {target_week}")
            cols = st.columns(7)
            for i, day in enumerate(st.session_state.plan[target_week].keys()):
                with cols[i]:
                    st.info(f"**{day}**")
                    meal = st.session_state.plan[target_week][day]
                    if meal and meal in st.session_state.library:
                        st.success(meal)
                        img = st.session_state.library[meal].get('image')
                        if img and os.path.exists(img):
                            st.image(img, use_container_width=True)
                    else: st.write("---")
        else:
            for week_name, data in st.session_state.plan.items():
                st.markdown(f"**{week_name}**")
                cols = st.columns(7)
                for i, (day, meal) in enumerate(data.items()):
                    with cols[i]:
                        st.caption(day)
                        st.write(f"🟢 **{meal}**" if meal else "---")
                st.divider()

with tab2:
    st.header("🛒 Shopping List")
    shop_week = st.selectbox("Generate list for:", list(st.session_state.plan.keys()))
    needed = []
    for day, meal in st.session_state.plan[shop_week].items():
        if meal in st.session_state.library:
            needed.extend(st.session_state.library[meal]['ingredients'])
    
    if needed:
        final_list = sorted(list(set(needed)))
        list_text = f"Grocery List for {shop_week}:\n" + "\n".join([f"- {item}" for item in final_list])
        st.download_button("📩 Download List (.txt)", list_text, file_name=f"Groceries_{shop_week}.txt")
        for item in final_list:
            st.checkbox(item, key=f"check_{item}_{shop_week}")
    else: st.write("Add meals to see ingredients!")

with tab3:
    st.header("📚 Manage Recipes")
    with st.expander("➕ Add New Recipe"):
        col_a, col_b = st.columns(2)
        with col_a:
            new_name = st.text_input("Meal Name")
            new_cat = st.selectbox("Category", ["Dinner", "Baking", "Garden Veggies", "Quick Meal", "Breakfast", "Other"])
            add_mode = st.radio("Input Method", ["Keyboard", "Photo"], horizontal=True)
        
        extracted_text = ""
        img_path = None
        with col_b:
            if add_mode == "Photo":
                uploaded_file = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])
                if uploaded_file:
                    img = Image.open(uploaded_file)
                    img_path = os.path.join(IMAGE_DIR, f"{new_name.replace(' ','_')}.jpg")
                    img.save(img_path)
                    img_np = np.array(img)
                    with st.spinner("Reading..."):
                        try:
                            results = get_reader().readtext(img_np)
                            extracted_text = "\n".join([res[1] for res in results])
                        except: st.error("Error reading image.")

        new_ingredients = st.text_area("Ingredients", value=extracted_text)
        if st.button("💾 Save Recipe", use_container_width=True):
            if new_name:
                st.session_state.library[new_name] = {
                    "ingredients": [i.strip() for i in new_ingredients.split("\n") if i.strip()],
                    "category": new_cat, "image": img_path
                }
                save_data()
                st.rerun()

    st.divider()
    lib_cols = st.columns(4)
    for i, (name, info) in enumerate(st.session_state.library.items()):
        with lib_cols[i % 4]:
            st.markdown(f"**{name}**")
            st.caption(info.get('category', 'Other'))
            img = info.get('image')
            if img and os.path.exists(img):
                st.image(img, use_container_width=True)
            if st.button("🗑️ Delete", key=f"del_{name}"):
                del st.session_state.library[name]
                save_data()
                st.rerun()