import streamlit as st
import json
import os
import base64
from io import StringIO
from copy import deepcopy
import pandas as pd

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
    original_data = load_json(stringio)
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


if "edited_data" not in st.session_state:
    st.session_state.edited_data = deepcopy(original_data)

if "changes_log" not in st.session_state:
    st.session_state.changes_log = []

service_keys = sorted({b['serviceKey'] for b in original_data})
selected_key = st.selectbox("Select a Service Key to Edit", service_keys)
edited_bouquet = find_bouquet(st.session_state.edited_data, selected_key)
original_bouquet = find_bouquet(original_data, selected_key)
service_name = name_map.get(selected_key, "Unknown service")

if not edited_bouquet:
    st.warning("No entry was found for the selected service key.")
    st.stop()

st.subheader(f"Editing Devices for Service Key: {selected_key} - {service_name}")

for i, device in enumerate(edited_bouquet["devices"]):
    with st.expander(f"{device['deviceType']} - {device['devicePlatform']}"):
        current = device.get("deviceConnectivity", [])
        new_connectivity = st.multiselect(
            "Connectivity options", 
            ["IPTV", "SATELLITE"], 
            default=current, 
            key=f"{selected_key}_{device['deviceType']}_{device['devicePlatform']}_{i}"
        )

        if set(current) != set(new_connectivity):
            device["deviceConnectivity"] = new_connectivity

            already_logged = any(
                log["Service Key"] == selected_key and
                log["Device Type"] == device["deviceType"] and
                log["Platform"] == device["devicePlatform"]
                for log in st.session_state.changes_log
            )

            if not already_logged:
                old_device = next(
                    (d for d in original_bouquet["devices"]
                     if d["deviceType"] == device["deviceType"] and d["devicePlatform"] == device["devicePlatform"]),
                    None
                )
                old_conn = old_device.get("deviceConnectivity", []) if old_device else []
                st.session_state.changes_log.append({
                    "Service Key": selected_key,
                    "Service Name": service_name,
                    "Device Type": device["deviceType"],
                    "Platform": device["devicePlatform"],
                    "Old Connectivity": ", ".join(old_conn),
                    "New Connectivity": ", ".join(new_connectivity)
                })

if st.button("Save Changes", icon="💾"):
    try:
        save_json(OUTPUT_FILE, st.session_state.edited_data)
        st.success(f"All changes saved to {OUTPUT_FILE}")
        st.markdown(file_download_link(OUTPUT_FILE, "Download updated JSON file"), unsafe_allow_html=True)
        if st.session_state.changes_log:
            st.subheader("Changed Devices")
            df = pd.DataFrame(st.session_state.changes_log)
            st.dataframe(df, use_container_width=True)
            
        else:
            st.info("No changes detected across service keys.")

    except Exception as e:
        st.error(f"Error saving file: {e}")


