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

if "temp_edits" not in st.session_state:
    st.session_state.temp_edits = {}


service_keys = sorted({b['serviceKey'] for b in original_data})
selected_key = st.selectbox("Select a Service Key to Edit", service_keys)
service_name = name_map.get(selected_key, "Unknown service")


edited_bouquet = find_bouquet(st.session_state.edited_data, selected_key)
original_bouquet = find_bouquet(original_data, selected_key)

if not edited_bouquet:
    st.warning("No entry was found for the selected service key.")
    st.stop()

st.subheader(f"Editing Devices for Service Key: {selected_key} - {service_name}")


if selected_key not in st.session_state.temp_edits:
    st.session_state.temp_edits[selected_key] = deepcopy(edited_bouquet)


temp_bouquet = st.session_state.temp_edits[selected_key]


for i, device in enumerate(temp_bouquet["devices"]):
    device_type = device["deviceType"]
    platform = device["devicePlatform"]
    widget_key = f"{selected_key}_{device_type}_{platform}_{i}"

    with st.expander(f"{device_type} - {platform}"):
        current_value = device.get("deviceConnectivity", [])
        new_value = st.multiselect(
            "Connectivity options",
            ["IPTV", "SATELLITE"],
            default=current_value,
            key=widget_key
        )
        device["deviceConnectivity"] = new_value


if st.button("Save Changes", icon="💾"):
    try:
        
        for service_key, updated_bouquet in st.session_state.temp_edits.items():
            main_bouquet = find_bouquet(st.session_state.edited_data, service_key)
            if main_bouquet:
                main_bouquet["devices"] = deepcopy(updated_bouquet["devices"])

        
        save_json(OUTPUT_FILE, st.session_state.edited_data)
        st.success(f"All changes saved to {OUTPUT_FILE}")
        st.markdown(file_download_link(OUTPUT_FILE, "Download updated JSON file"), unsafe_allow_html=True)

        
        with open(OUTPUT_FILE, 'r') as f:
            updated_data = json.load(f)

        change_log = []
        for original_entry in original_data:
            updated_entry = find_bouquet(updated_data, original_entry["serviceKey"])
            if not updated_entry:
                continue

            for orig_device in original_entry.get("devices", []):
                matching_device = next(
                    (d for d in updated_entry.get("devices", [])
                     if d["deviceType"] == orig_device["deviceType"]
                     and d["devicePlatform"] == orig_device["devicePlatform"]),
                    None
                )
                if matching_device:
                    old_conn = set(orig_device.get("deviceConnectivity", []))
                    new_conn = set(matching_device.get("deviceConnectivity", []))
                    if old_conn != new_conn:
                        change_log.append({
                            "Service Key": original_entry["serviceKey"],
                            "Service Name": name_map.get(original_entry["serviceKey"], "Unknown service"),
                            "Device Type": orig_device["deviceType"],
                            "Platform": orig_device["devicePlatform"],
                            "Old Connectivity": ", ".join(sorted(old_conn)),
                            "New Connectivity": ", ".join(sorted(new_conn))
                        })

        if change_log:
            st.subheader("Changed Devices (Based on File Comparison)")
            df = pd.DataFrame(change_log)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No changes detected in saved file.")

    except Exception as e:
        st.error(f"Error saving or comparing file: {e}")

