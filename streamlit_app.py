import streamlit as st
import json
import os
import shutil
import base64
from io import StringIO

NAME_MAPPING = "name_mapping.json"
OUTPUT_FILE = "updated_output.json"

def load_json(file_obj):
    return json.load(file_obj)

def save_json(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def load_service_names(mapping_file):
    with open(mapping_file, 'r') as f:
        data = json.load(f)
    return {str(service["sid"]): service["t"] for service in data["services"]}

def find_bouquet(data, service_key):
    for entry in data:
        if entry.get("serviceKey") == service_key:
            return entry
    return None

def file_download_link(file_path, label):
    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    href = f'<a href="data:application/json;base64,{b64}" download="{file_path}">{label}</a>'
    return href

st.set_page_config(page_title="Device Connectivity Manager", page_icon="sky.png", layout="wide")
st.title("📡 Device Connectivity Editor")

uploaded_file = st.file_uploader("Upload a Bouquet JSON File", type=["json"])

if not uploaded_file:
    st.warning("Please upload a JSON file to proceed.")
    st.stop()

try:
    stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
    data = load_json(stringio)
except Exception as e:
    st.error(f"Error reading uploaded file: {e}")
    st.stop()


if not os.path.exists(NAME_MAPPING):
    st.error(f"Could not find name mapping file: {NAME_MAPPING}")
    st.stop()

try:
    name_map = load_service_names(NAME_MAPPING)
except Exception as e:
    st.error(f"Error loading service name mapping: {e}")
    st.stop()

service_keys = sorted({b['serviceKey'] for b in data})
selected_key = st.selectbox("Select a Service Key to Edit", service_keys)
bouquet = find_bouquet(data, selected_key)

if not bouquet:
    st.warning("No entry was found for the selected service key.")
    st.stop()

service_t = name_map.get(selected_key, "Unknown service")
st.subheader(f"Editing Devices for Service Key: {selected_key} - {service_t}")

updated_devices = []
for device in bouquet["devices"]:
    with st.expander(f"{device['deviceType']} - {device['devicePlatform']}"):
        current = device.get("deviceConnectivity", [])
        new_connectivity = st.multiselect(
            "Connectivity options", 
            ["IPTV", "SATELLITE"], 
            default=current, 
            key=f"{device['deviceType']}_{device['devicePlatform']}"
        )
        device["deviceConnectivity"] = new_connectivity
        updated_devices.append(device)

if st.button("Save Changes", icon="💾"):
    try:
        save_json(OUTPUT_FILE, data)
        st.success(f"Changes saved to {OUTPUT_FILE}")
        if updated_devices:
           st.markdown(file_download_link(OUTPUT_FILE, "Click here to download the updated file"), unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error saving file: {e}")

