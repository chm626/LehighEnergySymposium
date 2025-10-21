# Main Streamlit application with modular tab structure
import streamlit as st
import importlib
from config.settings import Settings
from core.database import db_manager

# Page configuration
st.set_page_config(
    page_title=Settings.APP_TITLE,
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_module(module_name, class_name):
    """Dynamically load a module and return its class"""
    try:
        module = importlib.import_module(f"modules.{module_name}")
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        st.error(f"Failed to load module {module_name}: {e}")
        return None

def main():
    """Main application function"""
    
    # Header
    st.title(Settings.APP_TITLE)
    st.markdown(f"*{Settings.APP_DESCRIPTION}*")
    
    # Create tabs
    tab_names = [module['name'] for module in Settings.AVAILABLE_MODULES]
    tabs = st.tabs(tab_names)
    
    # Render each module in its tab
    for i, module_config in enumerate(Settings.AVAILABLE_MODULES):
        with tabs[i]:
            try:
                # Load and instantiate the module
                module_class = load_module(module_config['module'], module_config['class'])
                if module_class:
                    module_instance = module_class()
                    module_instance.render()
                else:
                    st.error(f"Could not load {module_config['name']} module")
                    
            except Exception as e:
                st.error(f"Error rendering {module_config['name']}: {e}")
    
    # Sidebar information
    with st.sidebar:
        st.header("About")
        st.write("This application provides comprehensive energy market analysis tools.")
        
        st.header("Database Status")
        if st.button("Test Database Connection"):
            try:
                if db_manager.test_connection():
                    st.success("✅ Database Connected")
                else:
                    st.error("❌ Database Connection Failed")
            except Exception as e:
                st.error(f"❌ Database Error: {e}")
        
        st.header("Available Modules")
        for module in Settings.AVAILABLE_MODULES:
            with st.expander(module['name']):
                st.write(module['description'])

if __name__ == "__main__":
    main()
