import streamlit as st
import time
import google.generativeai as genai
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import simpleSplit
from io import BytesIO
import os
import logging
import requests
import folium
from streamlit_folium import folium_static
from geopy.distance import geodesic

# Set up logging
logging.basicConfig(level=logging.INFO)

# Set up Gemini API
os.environ['GOOGLE_API_KEY'] = 'YOUR_GOOGLE_API_KEY'  # Replace with your actual API key
genai.configure(api_key=os.environ['GOOGLE_API_KEY'])

# Streamlit page configuration
st.set_page_config(page_title="Healthcare Assistant", layout="wide", initial_sidebar_state="expanded")

# Custom styling for the page
st.markdown("""
    <style>
        body {
            background-color: #f7f9fc;
            color: #2e3b4e;
            font-family: Arial, sans-serif;
        }
        h1 {
            font-size: 3rem;
            color: #005f73;
            text-align: center;
            margin-top: 20px;
        }
        .stTextArea textarea, .stTextInput input, .stNumberInput input {
            background-color: #e0f7fa;
            border: 1px solid #004d40;
            border-radius: 8px;
            padding: 10px;
            color: #004d40;
        }
        .stButton button {
            background-color: #0288d1;
            color: white;
            border-radius: 10px;
            font-weight: bold;
            padding: 10px 20px;
            font-size: 1rem;
        }
        .stSlider {
            color: #0288d1;
            border-radius: 8px;
        }
        .css-1lcbmhc {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 15px;
        }
        .css-1siy2j7 {
            font-size: 1.2rem;
            color: #004d40;
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

def query_healthcare_assistant(symptoms, age_category, symptom_severity):
    prompt = f"""
    Given the following symptoms: {symptoms}, severity: {symptom_severity}, list possible conditions and tailored medical advice for a {age_category}.

    Conditions:
    - condition 1
    - condition 2
    ...

    Advice:
    1. Step 1
    2. Step 2
    ...

    Medicine Recommendation:
    - For fever: Dolo 650, Paracetamol 500mg
    - For cold: Cetirizine, Vicks VapoRub
    """
    model = genai.GenerativeModel('gemini-pro')
    try:
        response = model.generate_content(prompt)
        if response and response.text:
            return response.text
        else:
            logging.error("No response text found.")
            return "Sorry, there was an error generating the response."
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return f"Sorry, there was an error generating the response. Error: {e}"

def create_pdf(report):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 50

    c.setFont("Helvetica-Bold", 20)
    c.setFillColorRGB(0.2, 0.4, 0.6)
    c.drawString(margin, height - margin, "Healthcare Report")

    c.setFont("Helvetica", 12)
    c.setFillColorRGB(0, 0, 0)
    y = height - margin - 30
    max_width = width - 2 * margin

    def draw_wrapped_text(c, text, x, y, max_width, font_name="Helvetica", font_size=12):
        lines = simpleSplit(text, font_name, font_size, max_width)
        for line in lines:
            if y < margin:
                c.showPage()
                c.setFont(font_name, font_size)
                y = height - margin
            c.drawString(x, y, line)
            y -= font_size + 4  # Increased line spacing for better readability
        return y

    sections = report.split('\n')
    for line in sections:
        if line.strip():
            if line.startswith('Conditions:'):
                c.setFont("Helvetica-Bold", 16)
                c.setFillColorRGB(0.4, 0.6, 0.8)
                y = draw_wrapped_text(c, line, margin, y, max_width, "Helvetica-Bold", 16)
                c.setFont("Helvetica", 12)
                c.setFillColorRGB(0, 0, 0)
                y -= 10  # Add space between sections
            elif line == 'Advice:':
                c.setFont("Helvetica-Bold", 16)
                c.setFillColorRGB(0.4, 0.6, 0.8)
                y = draw_wrapped_text(c, line, margin, y, max_width, "Helvetica-Bold", 16)
                c.setFont("Helvetica", 12)
                c.setFillColorRGB(0, 0, 0)
                y -= 10  # Add space between sections
            else:
                y = draw_wrapped_text(c, line, margin + 20, y, max_width - 20)
                y -= 10  # Add space between sections

    c.save()
    buffer.seek(0)
    return buffer

def get_coordinates(address):
    url = f"https://nominatim.openstreetmap.org/search?q={address}&format=json&limit=1"
    headers = {"User-Agent": "HealthcareAssistant/1.0"}
    response = requests.get(url, headers=headers)
    data = response.json()
    if data:
        return float(data[0]['lat']), float(data[0]['lon'])
    return None, None

def find_nearby_places(lat, lon, place_type, radius=5000):
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    (
      node["amenity"="{place_type}"](around:{radius},{lat},{lon});
      way["amenity"="{place_type}"](around:{radius},{lat},{lon});
      relation["amenity"="{place_type}"](around:{radius},{lat},{lon});
    );
    out center;
    """
    response = requests.get(overpass_url, params={'data': overpass_query})
    data = response.json()
    return data['elements']

def display_map(lat, lon, hospitals, pharmacies):
    m = folium.Map(location=[lat, lon], zoom_start=13)
    folium.Marker([lat, lon], popup="Your Location", icon=folium.Icon(color='red')).add_to(m)

    for hospital in hospitals:
        if 'lat' in hospital and 'lon' in hospital:
            folium.Marker(
                [hospital['lat'], hospital['lon']],
                popup=hospital.get('tags', {}).get('name', 'Hospital'),
                icon=folium.Icon(color='blue', icon='plus-sign')
            ).add_to(m)

    for pharmacy in pharmacies:
        if 'lat' in pharmacy and 'lon' in pharmacy:
            folium.Marker(
                [pharmacy['lat'], pharmacy['lon']],
                popup=pharmacy.get('tags', {}).get('name', 'Pharmacy'),
                icon=folium.Icon(color='green', icon='medkit')
            ).add_to(m)

    folium_static(m)

def display_nearby_facilities(lat, lon, hospitals, pharmacies):
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Nearby Hospitals:")
        for hospital in hospitals[:5]:  # Limit to top 5 results
            if 'tags' in hospital and 'name' in hospital['tags'] and 'lat' in hospital and 'lon' in hospital:
                distance = geodesic((lat, lon), (hospital['lat'], hospital['lon'])).km
                st.write(f"{hospital['tags']['name']} - {distance:.2f} km")

    with col2:
        st.subheader("Nearby Pharmacies:")
        for pharmacy in pharmacies[:5]:  # Limit to top 5 results
            if 'tags' in pharmacy and 'name' in pharmacy['tags'] and 'lat' in pharmacy and 'lon' in pharmacy:
                distance = geodesic((lat, lon), (pharmacy['lat'], pharmacy['lon'])).km
                st.write(f"{pharmacy['tags']['name']} - {distance:.2f} km")

def main():
    st.title("Clinical Prescription Chatbot")

    st.header("Symptom Analysis")
    age_category = st.selectbox("Select your age category:", ["Minor (under 18)", "Major (19-35)", "Senior (36+)"])
    symptoms = st.text_area("Describe your symptoms", "", placeholder="Enter your symptoms here...")
    symptom_severity = st.select_slider("Rate the severity of your symptoms", options=["Mild", "Moderate", "Severe"])

    st.header("Location Information")
    address = st.text_input("Enter your location:")
    search_radius = st.slider("Search radius for nearby facilities (km)", 1, 20, 5) * 1000  # Convert to meters

    if st.button("Analyze Symptoms and Find Nearby Facilities"):
        if symptoms and address and age_category:
            with st.spinner("Analyzing your symptoms and finding nearby facilities..."):
                progress = st.progress(0)
                for i in range(1, 101):
                    progress.progress(i)
                    time.sleep(0.05)  # Simulating a delay for the animation effect

                report = query_healthcare_assistant(symptoms, age_category, symptom_severity)
                lat, lon = get_coordinates(address)

                if lat and lon:
                    hospitals = find_nearby_places(lat, lon, "hospital", search_radius)
                    pharmacies = find_nearby_places(lat, lon, "pharmacy", search_radius)

                    st.subheader("Symptom Analysis")
                    st.write(report)

                    pdf = create_pdf(report)
                    st.download_button(
                        label="Download Report as PDF",
                        data=pdf,
                        file_name="healthcare_report.pdf",
                        mime="application/pdf"
                    )

                    st.subheader("Nearby Healthcare Facilities")
                    display_map(lat, lon, hospitals, pharmacies)
                    display_nearby_facilities(lat, lon, hospitals, pharmacies)
                else:
                    st.error("Unable to find coordinates for the given address. Please try again.")
        else:
            st.warning("Please enter your symptoms, location, and select your age category.")

    st.sidebar.title("About This Chatbot")
    st.sidebar.markdown("""
    Welcome to the **Healthcare Assistant**!
    This chatbot assists in:
    - Analyzing symptoms
    - Suggesting possible conditions        
    - Recommending medicines
    - Locating nearby healthcare facilities
    """)

    st.sidebar.header("Healthcare Resources")
    st.sidebar.markdown("""
    - [World Health Organization (WHO)](https://www.who.int/)
    - [Centers for Disease Control and Prevention (CDC)](https://www.cdc.gov/)
    - [National Health Service (NHS)](https://www.nhs.uk/)
    """)

    st.sidebar.header("How to Use")
    st.sidebar.markdown("""
    1. **Describe** your symptoms.
    2. **Select** your age category.
    3. **Enter** your location.
    4. Click **Analyze Symptoms** for analysis and nearby facilities.
    """)

if __name__ == "__main__":
    main()