import sys
from bs4 import BeautifulSoup
import json
import os

def extract_ptrade_api_info(html_path):
    """从Ptrade HTML文档中提取API信息"""
    try:
        # Read HTML file
        print(f"Reading HTML file: {html_path}")
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find main content
        main_content = soup.find('div', class_='markdown-body')
        if not main_content:
            main_content = soup.find('div', id='content')
        if not main_content:
            main_content = soup.body if soup.body else soup
        
        # Extract API information
        api_info = {
            "functions": [],
            "classes": [],
            "modules": []
        }
        
        # Look for headings that indicate API functions
        headings = main_content.find_all(['h1', 'h2', 'h3', 'h4'])
        
        current_section = ""
        for heading in headings:
            heading_text = heading.get_text().strip()
            
            # Check if this is a function section
            if '-' in heading_text and len(heading_text.split('-')) == 2:
                # This looks like a function: "function_name - description"
                parts = heading_text.split('-')
                func_name = parts[0].strip()
                description = parts[1].strip()
                
                # Find the next sibling elements to get parameters, returns, etc.
                next_element = heading.find_next_sibling()
                details = {
                    "name": func_name,
                    "description": description,
                    "usage": "",
                    "parameters": [],
                    "returns": "",
                    "example": ""
                }
                
                # Look for code blocks, parameter lists, etc.
                current_detail = ""
                element = next_element
                while element and element.name not in ['h1', 'h2', 'h3', 'h4']:
                    if element.name == 'p':
                        text = element.get_text().strip()
                        if text.startswith("接口说明"):
                            current_detail = "description"
                        elif text.startswith("参数"):
                            current_detail = "parameters"
                        elif text.startswith("返回"):
                            current_detail = "returns"
                        elif text.startswith("示例"):
                            current_detail = "example"
                        elif text.startswith("使用场景"):
                            current_detail = "usage"
                    elif element.name == 'pre':
                        code_text = element.get_text().strip()
                        if current_detail == "usage":
                            details["usage"] = code_text
                        elif current_detail == "example":
                            details["example"] = code_text
                    elif element.name == 'ul' or element.name == 'ol':
                        if current_detail == "parameters":
                            for li in element.find_all('li'):
                                details["parameters"].append(li.get_text().strip())
                    
                    element = element.find_next_sibling()
                
                api_info["functions"].append(details)
        
        # Save extracted information
        output_path = os.path.join(os.path.dirname(html_path), 'ptrade_api_info.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(api_info, f, ensure_ascii=False, indent=2)
        
        print(f"API information extracted and saved to {output_path}")
        return api_info
        
    except Exception as e:
        print(f"Error extracting Ptrade API info: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def create_api_mapping(jq_api_path, ptrade_api_info):
    """创建聚宽到Ptrade的API映射"""
    try:
        # Read聚宽API文档
        with open(jq_api_path, 'r', encoding='utf-8') as f:
            jq_content = f.read()
        
        # Basic API mapping
        api_mapping = {
            # Data APIs
            "get_price": "get_price",
            "get_current_data": "get_current_data",
            "get_fundamentals": "get_fundamentals",
            "get_index_stocks": "get_index_stocks",
            "get_industry_stocks": "get_industry_stocks",
            "get_concept_stocks": "get_concept_stocks",
            "get_all_securities": "get_all_securities",
            "get_security_info": "get_security_info",
            
            # Trading APIs
            "order": "order",
            "order_value": "order_value",
            "order_target": "order_target",
            "order_target_value": "order_target_value",
            "cancel_order": "cancel_order",
            "get_open_orders": "get_open_orders",
            
            # Account APIs
            "get_portfolio": "get_portfolio",
            "get_positions": "get_positions",
            "get_orders": "get_orders",
            "get_trades": "get_trades",
            
            # System APIs
            "log.info": "log.info",
            "log.warn": "log.warn",
            "log.error": "log.error",
            "record": "record",
            "plot": "plot",
            "set_benchmark": "set_benchmark",
            "set_option": "set_option",
            
            # Risk control APIs
            "set_slippage": "set_slippage",
            "set_commission": "set_commission",
            "set_price_limit": "set_price_limit",
            
            # Schedule APIs
            "run_daily": "run_daily",
            "run_weekly": "run_weekly",
            "run_monthly": "run_monthly"
        }
        
        # Save mapping
        mapping_path = os.path.join(os.path.dirname(jq_api_path), 'api_mapping.json')
        with open(mapping_path, 'w', encoding='utf-8') as f:
            json.dump(api_mapping, f, ensure_ascii=False, indent=2)
        
        print(f"API mapping created and saved to {mapping_path}")
        return api_mapping
        
    except Exception as e:
        print(f"Error creating API mapping: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Get the directory of the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define paths
    html_path = os.path.join(script_dir, "PtradeAPI.html")
    jq_api_path = os.path.join(script_dir, "jq_api_complete_documentation.md")
    
    # Check if files exist
    if not os.path.exists(html_path):
        print(f"Ptrade HTML file not found: {html_path}")
        sys.exit(1)
    
    if not os.path.exists(jq_api_path):
        print(f"聚宽API文档未找到: {jq_api_path}")
        sys.exit(1)
    
    # Extract Ptrade API information
    ptrade_info = extract_ptrade_api_info(html_path)
    
    # Create API mapping
    if ptrade_info:
        api_mapping = create_api_mapping(jq_api_path, ptrade_info)
        if api_mapping:
            print("API映射创建完成!")
        else:
            print("API映射创建失败!")
    else:
        print("Ptrade API信息提取失败!")