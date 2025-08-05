import streamlit as st
import json
import os
import base64
from copy import deepcopy
import pandas as pd

NAME_MAPPING = "name_mapping.json"
OUTPUT_FILE = "updated_output.json"
AUTOSAVE_FILE = "autosave.json"

DEFAULT_DEVICES = [
    {"provider": "SKY", "deviceType": "SETTOPBOX", "devicePlatform": "AMIDALA", "deviceConnectivity": []},
    {"provider": "SKY", "deviceType": "MOBILE", "devicePlatform": "IOS", "deviceConnectivity": []},
    {"provider": "SKY", "deviceType": "MOBILE", "devicePlatform": "ANDROID", "deviceConnectivity": []},
    {"provider": "SKY", "deviceType": "COMPUTER", "devicePlatform": "PC", "deviceConnectivity": []},
    {"provider": "SKY", "deviceType": "COMPUTER", "devicePlatform": "MAC", "deviceConnectivity": []},
    {"provider": "SKY", "deviceType": "TABLET", "devicePlatform": "IOS", "deviceConnectivity": []},
    {"provider": "SKY", "deviceType": "TABLET", "devicePlatform": "ANDROID", "deviceConnectivity": []},
    {"provider": "SKY", "deviceType": "CONSOLE", "devicePlatform": "XBOX", "deviceConnectivity": []},
    {"provider": "SKY", "deviceType": "CONSOLE", "devicePlatform": "PLAYSTATION", "deviceConnectivity": []},
    {"provider": "SKY", "deviceType": "TV", "devicePlatform": "LG", "deviceConnectivity": []},
    {"provider": "SKY", "deviceType": "TV", "devicePlatform": "SAMSUNG", "deviceConnectivity": []},
    {"provider": "SKY", "deviceType": "IPSETTOPBOX", "devicePlatform": "APPLETV", "deviceConnectivity": []},
]

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

def autosave_session(data):
    try:
        with open(AUTOSAVE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        st.error(f"Autosave failed: {e}")

def load_autosave():
    if os.path.exists(AUTOSAVE_FILE):
        try:
            with open(AUTOSAVE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Failed to load autosave: {e}")
    return None

st.set_page_config(page_title="Device Connectivity Manager", page_icon="sky.png", layout="wide")
st.title("📡 Device Connectivity Manager")

uploaded_file = st.file_uploader("Upload a Bouquet JSON File", type=["json"])


if "last_uploaded_filename" not in st.session_state:
    st.session_state.last_uploaded_filename = None

if uploaded_file and uploaded_file.name != st.session_state.last_uploaded_filename:
    if os.path.exists(AUTOSAVE_FILE):
        os.remove(AUTOSAVE_FILE)
    st.session_state.clear()
    st.session_state.last_uploaded_filename = uploaded_file.name
    st.markdown("<script>window.location.reload(true);</script>", unsafe_allow_html=True)

if not uploaded_file:
    autosaved = load_autosave()
    if autosaved:
        st.info("Restored session from autosave (no uploaded file found).")
        original_data = deepcopy(autosaved)
    else:
        st.warning("Please upload a JSON file to proceed.")
        st.stop()
else:
    try:
        original_data = load_json(uploaded_file)
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
if "page" not in st.session_state:
    st.session_state.page = "Edit"

page = st.sidebar.radio("Navigation", ["Edit", "Add", "Delete"])

if page == "Edit":
    service_keys = sorted(set(b['serviceKey'] for b in st.session_state.edited_data) | set(st.session_state.temp_edits.keys()))
    selected_key = st.selectbox("Select a Service Key to Edit", service_keys)
    service_name = name_map.get(selected_key, "Unknown service")

    if selected_key not in st.session_state.temp_edits:
        bouquet = find_bouquet(st.session_state.edited_data, selected_key)
        if bouquet:
            st.session_state.temp_edits[selected_key] = deepcopy(bouquet)

    bouquet = st.session_state.temp_edits[selected_key]
    st.subheader(f"Editing Devices for Service Key: {selected_key} - {service_name}")
    
    for i, device in enumerate(bouquet["devices"]):
        widget_key = f"{selected_key}_{device['deviceType']}_{device['devicePlatform']}_{i}"
        with st.expander(f"{device['deviceType']} - {device['devicePlatform']}"):
            new_val = st.multiselect("Connectivity", ["IPTV", "SATELLITE"], default=device["deviceConnectivity"], key=widget_key)
            device["deviceConnectivity"] = new_val

    if st.button("💾 Save Changes"):
        for key, val in st.session_state.temp_edits.items():
            existing = find_bouquet(st.session_state.edited_data, key)
            if existing:
                existing["devices"] = deepcopy(val["devices"])
            else:
                st.session_state.edited_data.append(deepcopy(val))

        save_json(OUTPUT_FILE, st.session_state.edited_data)
        autosave_session(st.session_state.edited_data)
        st.success("Changes saved!")
        st.markdown(file_download_link(OUTPUT_FILE, "Download updated JSON"), unsafe_allow_html=True)

        change_log = []
        existing_keys = {entry["serviceKey"] for entry in original_data}

        for entry in st.session_state.edited_data:
            key = entry["serviceKey"]
            service_name = name_map.get(key, "Unknown")
            if key not in existing_keys:
                for device in entry.get("devices", []):
                    change_log.append({
                        "Service Key": key,
                        "Service Name": service_name,
                        "Device Type": device["deviceType"],
                        "Platform": device["devicePlatform"],
                        "Old Connectivity": "N/A",
                        "New Connectivity": ", ".join(device.get("deviceConnectivity", [])),
                    })
            else:
                original_entry = find_bouquet(original_data, key)
                for orig_device in original_entry.get("devices", []):
                    match = next((d for d in entry.get("devices", []) if d["deviceType"] == orig_device["deviceType"] and d["devicePlatform"] == orig_device["devicePlatform"]), None)
                    if match:
                        old_conn = set(orig_device.get("deviceConnectivity", []))
                        new_conn = set(match.get("deviceConnectivity", []))
                        if old_conn != new_conn:
                            change_log.append({
                                "Service Key": key,
                                "Service Name": service_name,
                                "Device Type": orig_device["deviceType"],
                                "Platform": orig_device["devicePlatform"],
                                "Old Connectivity": ", ".join(old_conn),
                                "New Connectivity": ", ".join(new_conn),
                            })

        if change_log:
            st.subheader("Changed Devices")
            st.dataframe(pd.DataFrame(change_log))

elif page == "Add":
    st.subheader("Add New Service Key")
    new_key = st.text_input("Enter New Service Key")

    if new_key:
        if new_key in {b['serviceKey'] for b in st.session_state.edited_data} or new_key in st.session_state.temp_edits:
            st.warning("Service Key already exists.")
        else:
            if "add_device_temp" not in st.session_state:
                st.session_state.add_device_temp = deepcopy(DEFAULT_DEVICES)
            st.subheader("Set Connectivity for Default Devices")
            col1,col2,col3 = st.columns([1,1,1])
            with col1:
                if st.button ("Autofill All with IPTV"):
                    for device in st.session_state.add_device_temp:
                        device["deviceConnectivity"]=["IPTV"]
            with col2: 
                if st.button ("Autofill All with SATELLITE"):
                    for device in st.session_state.add_device_temp:
                        device["deviceConnectivity"] = ["SATELLITE"]
            with col3:
                if st.button ("Autofill All with SATELLITE & IPTV"):
                    for device in st.session_state.add_device_temp:
                        device["deviceConnectivity"] = ["SATELLITE", "IPTV"]
    

            for i, device in enumerate(st.session_state.add_device_temp):
                widget_key = f"add_{device['deviceType']}_{device['devicePlatform']}_{i}"
                with st.expander(f"{device['deviceType']} - {device['devicePlatform']}"):
                    conn = st.multiselect("Connectivity", ["IPTV", "SATELLITE"], default=device["deviceConnectivity"], key=widget_key)
                    st.session_state.add_device_temp[i]["deviceConnectivity"] = conn

            if st.button("Confirm and Add Service Key"):
                ref_entry = st.session_state.edited_data[0]
                new_entry = {
                    "bouquetId": ref_entry["bouquetId"],
                    "subBouquetId": ref_entry["subBouquetId"],
                    "serviceKey": new_key,
                    "devices": deepcopy(st.session_state.add_device_temp)
                }
                st.session_state.temp_edits[new_key] = new_entry
                del st.session_state.add_device_temp 
                st.success(f"Service Key {new_key} added! Now switch to 'Edit' page to make further changes if needed.")
                st.session_state.page = "Edit"

               
                st.session_state.edited_data.append(deepcopy(new_entry))
                autosave_session(st.session_state.edited_data)

elif page == "Delete":
    st.subheader("Delete Service Key")
    all_keys = sorted(set(b['serviceKey'] for b in st.session_state.edited_data) | set(st.session_state.temp_edits.keys()))
    to_delete = st.selectbox("Choose Service Key to Delete", all_keys)
    if st.button("Delete Selected Key"):
        st.session_state.edited_data = [b for b in st.session_state.edited_data if b['serviceKey'] != to_delete]
        st.session_state.temp_edits.pop(to_delete, None)
        save_json(OUTPUT_FILE, st.session_state.edited_data)
        autosave_session(st.session_state.edited_data)
        st.success(f"Service Key {to_delete} deleted.")
        st.markdown(file_download_link(OUTPUT_FILE, "Download updated JSON"), unsafe_allow_html=True)


