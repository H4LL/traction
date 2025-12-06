#!/usr/bin/env python3
"""
Traction Tenant Onboarding Flow Test Script

Tests the complete public reservation flow:
1. Public reservation creation (self-service)
2. Tenant check-in with reservation ID
3. Tenant configuration validation
4. cheqd DID creation testing
5. Public DID assignment
6. Final issuer status validation

Usage:
    python test-tenant-flow.py [--base-url BASE_URL] [--debug]
"""

import argparse
import json
import time
import sys
import requests
from typing import Dict, Any, Optional


class TractionTester:
    """Test the complete Traction tenant onboarding flow"""
    
    def __init__(self, base_url: str = "http://localhost:8032", debug: bool = False):
        self.base_url = base_url.rstrip('/')
        self.debug = debug
        self.session = requests.Session()
        self.tenant_token = None
        self.reservation_id = None
        self.reservation_pwd = None
        self.created_did = None
        
    def log(self, message: str, level: str = "INFO"):
        """Log messages with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def log_request(self, method: str, url: str, payload: Any = None, headers: Any = None):
        """Log HTTP request details if debug enabled"""
        if self.debug:
            self.log(f"REQUEST: {method} {url}", "DEBUG")
            if headers:
                self.log(f"HEADERS: {json.dumps(dict(headers), indent=2)}", "DEBUG")
            if payload:
                self.log(f"PAYLOAD: {json.dumps(payload, indent=2)}", "DEBUG")
                
    def log_response(self, response: requests.Response):
        """Log HTTP response details if debug enabled"""
        if self.debug:
            self.log(f"RESPONSE: {response.status_code} {response.reason}", "DEBUG")
            self.log(f"RESPONSE HEADERS: {json.dumps(dict(response.headers), indent=2)}", "DEBUG")
            try:
                content = response.json()
                self.log(f"RESPONSE BODY: {json.dumps(content, indent=2)}", "DEBUG")
            except:
                self.log(f"RESPONSE BODY (text): {response.text}", "DEBUG")
    
    def make_request(self, method: str, endpoint: str, payload: Any = None, 
                    headers: Optional[Dict] = None, use_auth: bool = False) -> requests.Response:
        """Make HTTP request with proper logging and error handling"""
        url = f"{self.base_url}{endpoint}"
        req_headers = headers or {}
        
        if use_auth and self.tenant_token:
            req_headers['Authorization'] = f'Bearer {self.tenant_token}'
            
        self.log_request(method, url, payload, req_headers)
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, headers=req_headers)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=payload, headers=req_headers)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=payload, headers=req_headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            self.log_response(response)
            return response
            
        except Exception as e:
            self.log(f"Request failed: {str(e)}", "ERROR")
            raise
    
    def step_1_create_public_reservation(self) -> bool:
        """Step 1: Create public reservation (self-service)"""
        self.log("=== STEP 1: Create Public Reservation ===")
        
        payload = {
            "tenant_name": f"test-tenant-{int(time.time())}",
            "contact_email": "test@example.com"
        }
        
        try:
            response = self.make_request('POST', '/multitenancy/reservations', payload)
            
            if response.status_code == 200:
                data = response.json()
                self.reservation_id = data.get('reservation_id')
                self.reservation_pwd = data.get('reservation_pwd')
                self.log(f"✅ Reservation created successfully: {self.reservation_id}")
                self.log(f"Reservation password: {self.reservation_pwd}")
                return True
            else:
                self.log(f"❌ Failed to create reservation: {response.status_code}", "ERROR")
                self.log(f"Response: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Exception during reservation creation: {str(e)}", "ERROR")
            return False
    
    def step_2_tenant_checkin(self) -> bool:
        """Step 2: Check in as tenant with reservation ID"""
        self.log("=== STEP 2: Tenant Check-In ===")
        
        if not self.reservation_id:
            self.log("❌ No reservation ID available", "ERROR")
            return False
            
        payload = {
            "reservation_pwd": self.reservation_pwd  # Use the password from reservation
        }
        
        try:
            response = self.make_request('POST', f'/multitenancy/reservations/{self.reservation_id}/check-in', payload)
            
            if response.status_code == 200:
                data = response.json()
                self.tenant_token = data.get('token')
                if self.tenant_token:
                    self.log("✅ Tenant check-in successful")
                    self.log(f"JWT token obtained (length: {len(self.tenant_token)})")
                    return True
                else:
                    self.log("❌ No token in check-in response", "ERROR")
                    return False
            else:
                self.log(f"❌ Failed to check in: {response.status_code}", "ERROR")
                self.log(f"Response: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Exception during check-in: {str(e)}", "ERROR")
            return False
    
    def step_3_validate_configuration(self) -> bool:
        """Step 3: Validate tenant and server configuration"""
        self.log("=== STEP 3: Validate Configuration ===")
        
        # Check tenant config
        try:
            response = self.make_request('GET', '/tenant/config', use_auth=True)
            if response.status_code == 200:
                config = response.json()
                self.log("✅ Tenant config retrieved")
                if self.debug:
                    self.log(f"Tenant config: {json.dumps(config, indent=2)}")
            else:
                self.log(f"❌ Failed to get tenant config: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Exception getting tenant config: {str(e)}", "ERROR")
            return False
            
        # Check server config for cheqd settings
        try:
            response = self.make_request('GET', '/status/config', use_auth=True)
            if response.status_code == 200:
                server_config = response.json()
                self.log("✅ Server config retrieved")
                
                # Check for cheqd plugin configuration
                plugin_config = server_config.get('config', {}).get('plugin_config', {})
                cheqd_config = plugin_config.get('cheqd', {})
                
                if cheqd_config:
                    self.log("✅ cheqd plugin configuration found")
                    self.log(f"Network: {cheqd_config.get('network', 'not set')}")
                    self.log(f"Registrar URL: {cheqd_config.get('registrar_url', 'not set')}")
                    self.log(f"Resolver URL: {cheqd_config.get('resolver_url', 'not set')}")
                else:
                    self.log("⚠️  No cheqd plugin configuration found in server config", "WARN")
                    
                # Check wallet type
                wallet_type = server_config.get('config', {}).get('wallet', {}).get('type')
                if wallet_type == 'askar-anoncreds':
                    self.log("✅ Wallet type is askar-anoncreds (required for cheqd)")
                else:
                    self.log(f"⚠️  Wallet type is {wallet_type}, cheqd requires askar-anoncreds", "WARN")
                    
                if self.debug:
                    self.log(f"Server config: {json.dumps(server_config, indent=2)}")
                    
                return True
            else:
                self.log(f"⚠️  Failed to get server config: {response.status_code}, continuing without validation", "WARN")
                return True  # Continue even if server config fails
                
        except Exception as e:
            self.log(f"⚠️  Exception getting server config: {str(e)}, continuing", "WARN")
            return True  # Continue even if server config fails
    
    def step_4_create_cheqd_did(self) -> bool:
        """Step 4: Create cheqd DID"""
        self.log("=== STEP 4: Create cheqd DID ===")
        
        # Test different payload formats to find the right one
        payloads_to_test = [
            {
                "options": {
                    "network": "xanadu",
                    "key_type": "ed25519"
                }
            },
            {
                "options": {
                    "network": "xanadu",
                    "key_type": "ed25519",
                    "method_specific_id_algo": "uuid"
                }
            },
            {
                "options": {
                    "network": "xanadu",
                    "key_type": "ed25519"
                },
                "features": {}
            }
        ]
        
        for i, payload in enumerate(payloads_to_test):
            self.log(f"--- Testing payload format {i+1} ---")
            
            try:
                response = self.make_request('POST', '/did/cheqd/create', payload, use_auth=True)
                
                if response.status_code == 200:
                    data = response.json()
                    # cheqd DID endpoint returns DID at root level, not in 'result'
                    did = data.get('did') or data.get('result', {}).get('did')
                    if did:
                        self.created_did = did
                        self.log(f"✅ cheqd DID created successfully: {did}")
                        return True
                    else:
                        self.log("❌ No DID in successful response", "ERROR")
                        self.log(f"Response data: {json.dumps(data, indent=2)}", "ERROR")
                        
                elif response.status_code == 500:
                    self.log(f"❌ Server error creating DID (payload {i+1}): {response.status_code}", "ERROR")
                    try:
                        error_data = response.json()
                        self.log(f"Error details: {json.dumps(error_data, indent=2)}", "ERROR")
                    except:
                        self.log(f"Error response (text): {response.text}", "ERROR")
                else:
                    self.log(f"❌ Failed to create DID (payload {i+1}): {response.status_code}", "ERROR")
                    self.log(f"Response: {response.text}", "ERROR")
                    
            except Exception as e:
                self.log(f"❌ Exception during DID creation (payload {i+1}): {str(e)}", "ERROR")
                
        self.log("❌ All payload formats failed", "ERROR")
        return False
    
    def step_5_assign_public_did(self) -> bool:
        """Step 5: Assign the created DID as public DID"""
        self.log("=== STEP 5: Assign Public DID ===")
        
        if not self.created_did:
            self.log("❌ No DID created to assign", "ERROR")
            return False
            
        try:
            response = self.make_request('POST', f'/wallet/did/public?did={self.created_did}', 
                                      {}, use_auth=True)
            
            if response.status_code == 200:
                self.log(f"✅ Public DID assigned successfully: {self.created_did}")
                
                # Verify assignment
                response = self.make_request('GET', '/wallet/did/public', use_auth=True)
                if response.status_code == 200:
                    public_did_data = response.json()
                    assigned_did = public_did_data.get('result', {}).get('did')
                    if assigned_did == self.created_did:
                        self.log("✅ Public DID assignment verified")
                        return True
                    else:
                        self.log(f"❌ DID assignment mismatch. Expected: {self.created_did}, Got: {assigned_did}", "ERROR")
                        return False
                else:
                    self.log(f"❌ Failed to verify public DID: {response.status_code}", "ERROR")
                    return False
            else:
                self.log(f"❌ Failed to assign public DID: {response.status_code}", "ERROR")
                self.log(f"Response: {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Exception during public DID assignment: {str(e)}", "ERROR")
            return False
    
    def step_6_validate_issuer_status(self) -> bool:
        """Step 6: Validate final issuer status"""
        self.log("=== STEP 6: Validate Issuer Status ===")
        
        try:
            # Check if tenant is now ready for issuance
            response = self.make_request('GET', '/wallet/did/public', use_auth=True)
            if response.status_code == 200:
                public_did_data = response.json()
                if public_did_data.get('result'):
                    self.log("✅ Tenant has public DID - ready for issuance")
                    return True
                else:
                    self.log("❌ No public DID found", "ERROR")
                    return False
            else:
                self.log(f"❌ Failed to check issuer status: {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Exception during issuer status check: {str(e)}", "ERROR")
            return False
    
    def run_full_test(self) -> bool:
        """Run the complete test flow"""
        self.log("🚀 Starting Traction Tenant Onboarding Flow Test")
        self.log(f"Base URL: {self.base_url}")
        self.log(f"Debug mode: {self.debug}")
        
        steps = [
            ("Create Public Reservation", self.step_1_create_public_reservation),
            ("Tenant Check-In", self.step_2_tenant_checkin),
            ("Validate Configuration", self.step_3_validate_configuration),
            ("Create cheqd DID", self.step_4_create_cheqd_did),
            ("Assign Public DID", self.step_5_assign_public_did),
            ("Validate Issuer Status", self.step_6_validate_issuer_status),
        ]
        
        results = {}
        
        for step_name, step_func in steps:
            self.log(f"\n🔄 Executing: {step_name}")
            success = step_func()
            results[step_name] = success
            
            if success:
                self.log(f"✅ {step_name} completed successfully")
            else:
                self.log(f"❌ {step_name} failed")
                break
                
        # Final summary
        self.log("\n📊 TEST SUMMARY")
        self.log("=" * 50)
        
        all_passed = True
        for step_name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            self.log(f"{step_name}: {status}")
            if not success:
                all_passed = False
                
        if all_passed:
            self.log("\n🎉 ALL TESTS PASSED - Tenant onboarding flow working correctly!")
            self.log(f"Created DID: {self.created_did}")
        else:
            self.log(f"\n💥 TESTS FAILED - Issue identified in tenant onboarding flow")
            
        return all_passed


def main():
    parser = argparse.ArgumentParser(description='Test Traction tenant onboarding flow')
    parser.add_argument('--base-url', 
                       default='http://localhost:8032',
                       help='Base URL for Traction tenant-proxy (default: http://localhost:8032)')
    parser.add_argument('--debug', 
                       action='store_true',
                       help='Enable detailed debug logging')
    
    args = parser.parse_args()
    
    tester = TractionTester(base_url=args.base_url, debug=args.debug)
    success = tester.run_full_test()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()