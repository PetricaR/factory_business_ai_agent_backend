"""
Streamlit Factory AI Agent - SSE CLIENT (FIXED!)
Properly creates sessions on backend before making requests
Romanian Business Intelligence Multi-Agent System
"""

import streamlit as st
import json
import time
import uuid
import os
import logging
import requests
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Iterator

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')
logger = logging.getLogger(__name__)

# Import Google Auth
try:
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account, id_token
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False
    st.warning("⚠️ google-auth not available")

# Page config
st.set_page_config(
    page_title="Factory AI - SSE",
    page_icon="🏭",
    layout="wide"
)

# CSS
st.markdown("""
<style>
    .streaming-text { animation: pulse 1.5s ease-in-out infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
    .status-streaming { background: #2196F3; color: white; padding: 5px 12px; 
                       border-radius: 20px; animation: pulse 1.5s ease-in-out infinite; }
    .status-connected { background: #4caf50; color: white; padding: 5px 12px; border-radius: 20px; }
</style>
""", unsafe_allow_html=True)


class ADKSSEClient:
    """
    FIXED Client for ADK Backend
    Creates sessions on backend before streaming
    """
    
    def __init__(self, base_url: str, app_name: str = "agents",
                 service_account_path: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.app_name = app_name
        self.user_id = None
        self.session_id = None
        self.credentials = None
        
        logger.info(f"ADK SSE Client (FIXED!)")
        logger.info(f"  Backend: {self.base_url}")
        logger.info(f"  Endpoint: /run_sse")
        
        if service_account_path and os.path.exists(service_account_path):
            try:
                self.credentials = service_account.IDTokenCredentials.from_service_account_file(
                    service_account_path,
                    target_audience=base_url
                )
                logger.info(f"✓ Service account loaded")
            except Exception as e:
                logger.error(f"Failed to load SA: {e}")
    
    def get_auth_token(self) -> Optional[str]:
        """Get authentication token"""
        if not GOOGLE_AUTH_AVAILABLE:
            return None
        
        try:
            if self.credentials:
                auth_req = Request()
                self.credentials.refresh(auth_req)
                return self.credentials.token
            
            # Try application default
            auth_req = Request()
            token = id_token.fetch_id_token(auth_req, self.base_url)
            return token
        
        except Exception as e:
            logger.error(f"Auth failed: {e}")
            return None
    
    def create_session_on_backend(self, user_id: str, session_id: str) -> bool:
        """
        Create session on backend BEFORE making requests
        This is the KEY FIX for "Session not found" error
        """
        token = self.get_auth_token()
        if not token:
            logger.error("Cannot create session: No auth token")
            return False
        
        # Use the sessions API endpoint to create session
        url = f"{self.base_url}/apps/{self.app_name}/users/{user_id}/sessions"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "session_id": session_id,
            "state": {}  # Initial empty state
        }
        
        try:
            logger.info(f"Creating session on backend: {session_id}")
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code in [200, 201]:
                logger.info(f"✓ Session created: {session_id}")
                return True
            elif response.status_code == 409:
                # Session already exists, that's ok
                logger.info(f"✓ Session already exists: {session_id}")
                return True
            else:
                logger.error(f"Failed to create session: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return False
    
    def initialize_session(self, user_id: str) -> bool:
        """Initialize session"""
        self.user_id = user_id
        self.session_id = str(uuid.uuid4())
        logger.info(f"Session ID: {self.session_id}")
        
        # CRITICAL FIX: Create session on backend
        return self.create_session_on_backend(user_id, self.session_id)
    
    def stream_query(self, message: str, streaming: bool = True) -> Iterator[dict]:
        """
        Stream query via SSE (Server-Sent Events)
        """
        
        # Get auth token
        token = self.get_auth_token()
        if not token:
            yield {"type": "error", "content": "Authentication required"}
            return
        
        # Build request
        url = f"{self.base_url}/run_sse"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        
        payload = {
            "app_name": self.app_name,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "new_message": {
                "role": "user",
                "parts": [{"text": message}]
            },
            "streaming": streaming
        }
        
        logger.info(f"POST {url}")
        logger.info(f"Session: {self.session_id}")
        
        try:
            # SSE request with streaming
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                stream=True,
                timeout=120
            )
            
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                error_text = response.text[:500]
                logger.error(f"Error response: {error_text}")
                yield {
                    "type": "error",
                    "content": f"HTTP {response.status_code}: {error_text}"
                }
                return
            
            # Parse SSE stream
            full_text = ""
            event_count = 0
            
            for line in response.iter_lines():
                if not line:
                    continue
                
                try:
                    line_str = line.decode('utf-8')
                    
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]
                        event = json.loads(data_str)
                        event_count += 1
                        
                        logger.debug(f"SSE event #{event_count}: {event.get('type', 'unknown')}")
                        
                        # Parse ADK event format
                        if "content" in event:
                            content = event["content"]
                            role = content.get("role")
                            
                            if role == "model":
                                parts = content.get("parts", [])
                                for part in parts:
                                    if "text" in part:
                                        text_chunk = part["text"]
                                        full_text += text_chunk
                                        
                                        yield {
                                            "type": "text_chunk",
                                            "content": text_chunk,
                                            "full_text": full_text
                                        }
                                    
                                    elif "function_call" in part:
                                        func_call = part["function_call"]
                                        yield {
                                            "type": "tool_call",
                                            "function": func_call.get("name"),
                                            "content": f"🔧 {func_call.get('name')}"
                                        }
                
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse: {line_str[:100]}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing line: {e}")
                    continue
            
            # Final response
            if full_text:
                logger.info(f"Stream complete: {event_count} events, {len(full_text)} chars")
                yield {"type": "final", "content": full_text}
            else:
                yield {"type": "error", "content": "No response received"}
        
        except requests.exceptions.Timeout:
            logger.error("Request timeout")
            yield {"type": "error", "content": "Request timeout (120s)"}
        
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            yield {"type": "error", "content": f"Connection error: {str(e)}"}
        
        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield {"type": "error", "content": f"Error: {str(e)}"}


def find_service_accounts() -> list:
    """Find service account files"""
    found = []
    for path in [".", "./auth", "../auth"]:
        try:
            p = Path(path)
            if p.exists():
                for f in p.glob("*.json"):
                    if "application_default" not in f.name:
                        found.append(str(f))
        except:
            pass
    return found


def init_session_state():
    """Initialize state"""
    defaults = {
        'messages': [],
        'client': None,
        'connected': False,
        'streaming': False,
        'user_id': f"user_{int(time.time())}"
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar():
    """Sidebar"""
    with st.sidebar:
        st.title("⚙️ Configuration")
        
        st.success("✅ FIXED: Creates sessions properly!")
        st.caption("Sessions are now created on backend before requests")
        
        st.markdown("---")
        
        st.subheader("🔐 Authentication")
        sa_files = find_service_accounts()
        
        if sa_files:
            st.success(f"✅ Found {len(sa_files)} service account(s)")
            sa_file = st.selectbox("Service Account", ["None"] + sa_files, 
                                  index=1 if sa_files else 0)
        else:
            st.info("Place service account in ./auth/")
            sa_file = st.text_input("Service Account Path", 
                                   placeholder="./auth/service-account.json")
        
        st.markdown("---")
        
        st.subheader("🎯 Backend")
        backend_url = st.text_input(
            "Backend URL",
            value=os.getenv("BACKEND_URL", 
                          "https://factory-ai-agent-backend-845266575866.europe-west4.run.app")
        )
        
        app_name = st.text_input("App Name", value=os.getenv("APP_NAME", "agents"))
        user_id = st.text_input("User ID", value=st.session_state.user_id)
        st.session_state.user_id = user_id
        
        st.markdown("---")
        
        if st.button("🔌 Connect", use_container_width=True, type="primary"):
            sa_path = sa_file if sa_file != "None" and sa_file else None
            
            with st.spinner("Connecting..."):
                try:
                    st.session_state.client = ADKSSEClient(
                        backend_url, app_name, service_account_path=sa_path
                    )
                    
                    if st.session_state.client.initialize_session(user_id):
                        st.session_state.connected = True
                        st.success("✅ Connected & Session Created!")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Failed to create session on backend")
                
                except Exception as e:
                    st.error(f"Error: {e}")
                    logger.error(f"Connection error: {e}")
        
        st.markdown("---")
        st.subheader("📊 Status")
        
        if st.session_state.streaming:
            st.markdown('<span class="status-streaming">🔵 Streaming</span>', 
                       unsafe_allow_html=True)
        elif st.session_state.connected:
            st.markdown('<span class="status-connected">🟢 Connected (SSE)</span>', 
                       unsafe_allow_html=True)
            if st.session_state.client:
                st.caption(f"Session: {st.session_state.client.session_id[:12]}...")
        else:
            st.markdown("🔴 Disconnected")
        
        st.markdown("---")
        st.subheader("💡 Quick Actions")
        
        if st.button("🏢 Analyze Company", use_container_width=True):
            st.session_state.quick_query = "Ce îmi poți spune despre SEFINNI din Buzau?"
            st.rerun()
        
        if st.button("💰 Financials", use_container_width=True):
            st.session_state.quick_query = "Analizeaza CUI 35790107"
            st.rerun()
        
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        st.markdown("---")
        with st.expander("ℹ️ What Was Fixed"):
            st.markdown("""
            **The Problem:**
            - Client was generating session_id locally
            - Backend didn't know about this session
            - Resulted in "Session not found" error
            
            **The Solution:**
            - Now creates session on backend first
            - Uses `/apps/{app_name}/users/{user_id}/sessions` endpoint
            - Then uses that session for `/run_sse` requests
            
            **Flow:**
            1. Generate session_id
            2. **Create session on backend** ← NEW!
            3. Use session_id for queries
            """)


def stream_to_ui(client, message: str, placeholder):
    """Stream to UI"""
    full_response = ""
    steps_container = st.container()
    
    try:
        for event in client.stream_query(message):
            event_type = event.get("type")
            
            if event_type == "text_chunk":
                full_response = event.get("full_text", "")
                placeholder.markdown(full_response + " ▌")
            
            elif event_type == "tool_call":
                with steps_container:
                    st.info(event.get("content"))
            
            elif event_type == "final":
                full_response = event.get("content", full_response)
                break
            
            elif event_type == "error":
                error_msg = event.get("content", "Unknown error")
                placeholder.error(f"❌ {error_msg}")
                return None
    
    except Exception as e:
        logger.error(f"Stream error: {e}")
        placeholder.error(f"Error: {e}")
        return None
    
    steps_container.empty()
    if full_response:
        placeholder.markdown(full_response)
        return full_response
    else:
        placeholder.warning("No response received")
        return None


def main():
    """Main app"""
    init_session_state()
    render_sidebar()
    
    st.title("🏭 Factory AI Agent")
    st.markdown("**SSE Streaming Client (FIXED!)**")
    
    if not st.session_state.connected or not st.session_state.client:
        st.warning("⚠️ Please connect using the sidebar")
        
        st.info("""
        **Key Fix Applied:**
        
        The client now properly creates sessions on the backend **before** making requests.
        
        This fixes the "Session not found" error!
        """)
        
        return
    
    # Chat
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    if 'quick_query' in st.session_state:
        prompt = st.session_state.quick_query
        del st.session_state.quick_query
    else:
        prompt = st.chat_input("Ask about Romanian companies...")
    
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            placeholder = st.empty()
            st.session_state.streaming = True
            
            try:
                response = stream_to_ui(st.session_state.client, prompt, placeholder)
                
                if response:
                    st.session_state.messages.append({"role": "assistant", "content": response})
            
            finally:
                st.session_state.streaming = False


if __name__ == "__main__":
    main()