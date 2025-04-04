import streamlit as st
import pandas as pd
import datetime
import pydeck as pdk
import logging 


###############################################################################
# 1. Logging Setup
###############################################################################
def get_logger():
    logger = logging.getLogger("streamlit-snowflake")
    if not hasattr(logger, 'handler_set'):  # Check if handler is already set
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.handler_set = True  # Mark the handler as set
    return logger

logger = get_logger()
###############################################################################
# 2. Snowflake Connection Handling (Persistent Session)
###############################################################################

@st.cache_resource(ttl=3300, show_spinner="Connecting to Snowflake...")  # 55 min
def get_snowflake_session():
    """Create a persistent Snowflake session that stays alive."""
    conn = st.connection("Wismo")
    session = conn.session()
    logger.info("Session SUCCESSFULLY started...")
    return session
    

def close_snowflake_session():
    """Closes the Snowflake session when the app exits."""
    if "snowflake_session" in st.session_state:
        try:
            st.session_state.snowflake_session.close()
            del st.session_state.snowflake_session
            logger.info("Snowflake session closed.")
        except Exception as e:
            logger.error(f"Error closing Snowflake session: {e}")


###############################################################################
# 1. Page Config
###############################################################################
st.set_page_config(page_title="Order Detail", layout="centered")

# Include Poppins font from Google Fonts
st.markdown(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">
    """,
    unsafe_allow_html=True,
)

# Inject minimal CSS
st.markdown(
    """
    <style>
    /* Center the overall container */
    .main {
        max-width: 1000px;
        margin: 0 auto;
    }
    /* Basic styling for bullet statuses */
    .status-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 0.5rem;
        margin-top: 0.3rem;
    }
    /* Colors for statuses */
    .status-dot.blue { background-color: #3781ad; }
    .status-dot.black { background-color: #2c3143; }
    .status-dot.gray { background-color: #b0ccca; }
    /* Text colors */
    body {
        color: #2c3143;
        font-family: 'Poppins', sans-serif !important; /* Apply Poppins to the entire body and use !important to increase specificity */
    }
    /* Header colors */
    h3 {
        color: #3781ad;
        font-family: 'Poppins', sans-serif !important; /* Ensure headers also use Poppins */
    }
    /* Map styling (example) */
    .stMap {
        border-radius: 10px;
    }
    /* Style the search bar */
    .stTextInput>div>div>input {
    font-family: 'Poppins', sans-serif !important;
    border: 1px solid #ccc;
    border-radius: 8px;
    padding: 8px 10px;
    color: #2c3143;
    }
    /* Style the search bar label */
    .stTextInput label {
        font-family: 'Poppins', sans-serif !important;
        font-size: 0.9em; /* Matches the status description size */
        color: gray;       /* Matches the status description color */
    }
    /* Style the search bar input text */
    .stTextInput>div>div>input {
        font-family: 'Poppins', sans-serif !important;
        font-size: 0.9em; /* Match the status description size */
        color: #2c3143;
        border: 1px solid #ccc;
        border-radius: 5px;
        padding: 8px 10px;
    }
    /* Style for Order Status, Order Date, Tracking # labels */
    .order-info-label {
        font-family: 'Poppins', sans-serif !important;
        font-size: 0.75em !important;
        color: #737373 !important;
        margin-bottom: 0 !important; /* Remove bottom margin */
        margin-top: 0 !important;    /* Remove top margin as well */
    }

    /* Style for the values (Backordered, Date, Tracking Number) */
    .order-info-value {
        font-family: 'Poppins', sans-serif !important;
        font-size: 0.75em !important;
        color: #737373 !important;
        font-weight: normal;
        margin-bottom: 0 !important; /* Remove bottom margin */
        margin-top: 0 !important;    /* Remove top margin */
    }

    /* Style for the container div */
    .order-info-container {
        margin-bottom: -4px !important; /* Reduce space below the whole div */
        margin-top: -4px !important;    /* Reduce space above the whole div */
        padding-top: -4px !important;   /* Reduce space inside div */
        padding-bottom: -4px !important; /* Reduce space inside div */
    }

     /* Style the outer container for product substitutions */
    .substitution-item {
        border: 1px solid #ccc;
        border-radius: 15px;
        padding: 10px;
        margin-bottom: 10px;
        display: flex;
        flex-direction: column;
        /* Removed flex: 1; */
        /* Optionally add min-height if you want a base height */
        min-height: 380px;
    }
    /* Style the blue boxes in product substitutions with the desired gradient */
    .blue-box {
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        font-family: 'Poppins', sans-serif !important;
        min-height: 120px;
        margin: -10px;
        padding: 10px;
        border-radius: 10px 10px 0 0;
        margin-bottom: 15px;
        /* Gradient Background from left to right */
        background-image: linear-gradient(to right, #3781ad, #53a69a);
        /* Optional: Add a subtle box-shadow for depth */
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }



    /* Style the white boxes in product substitutions */
    .white-box {
        display: flex;
        flex-direction: column;
        justify-content: space-between; /* Push the button to the bottom */
        flex-grow: 1; /* Make it grow to fill available space */
        font-family: 'Poppins', sans-serif !important;
        min-height: 200px; /* Adjusted min-height */
        padding: 0 10px; /* Keep the padding for internal content */
    }

    .white-box > div:first-child {
    margin-top: 15px; /* Adjust this value to control the spacing */
    }

    /* Decrease line spacing within blue boxes */
    .blue-box b,
    .blue-box p {
        margin-bottom: 5px; /* Adjust as needed */
        line-height: 1.2; /* Adjust as needed */
    }

    /* Decrease line spacing within white boxes */
    .white-box div,
    .white-box p {
        margin-bottom: 5px; /* Adjust as needed */
        line-height: 1.2; /* Adjust as needed */
    }

    /* Ensure the outer container takes up full height */
    .st-emotion-cache-16txtl3 { /* Adjust if needed */
        display: flex;
        flex-direction: column;
        height: 100%;
    }

    /* Apply Poppins to markdown elements */
    div, p, span, a {
        font-family: 'Poppins', sans-serif !important;
    }
    /* Style the order buttons */
    button {
        font-family: 'Poppins', sans-serif !important;
        font-size: 11px; /* Keep the font size small */
        font-weight: 600;
        border: none;
        background-color: #2c3143;
        color: white;
        border-radius: 20px;
        cursor: pointer;
        padding: 10px 18px; /* Increase padding to make the button bigger */
    }
    </style>

    """,
    unsafe_allow_html=True,
)

STATUS_ORDER = [
    "Label Created",
    "Shipment Information Received",
    "Picked Up",
    "Departed from Origin Facility",
    "In Transit",
    "Arrived at Carrier Facility",
    "Out for Delivery",
    "Delivered",
]

STATUS_DESCRIPTIONS = {
    "Label Created": "A shipping label has been created for the order.",
    "Shipment Information Received": "The carrier has received shipment information.",
    "Picked Up": "The package has been picked up by the carrier.",
    "Departed from Origin Facility": "The package has left the origin facility.",
    "In Transit": "The package is in transit to its destination.",
    "Arrived at Carrier Facility": "The package has arrived at a carrier facility.",
    "Out for Delivery": "The package is out for delivery.",
    "Delivered": "The package has been delivered.",
}

KNOWN_CITIES = {
    'Boston, MA': (42.3602534, -71.0582912),
    'Los Angeles, CA': (34.0522342, -118.2436849),
    'Chicago, IL': (41.8781136, -87.6297982),
    'Denver, CO': (39.7391536, -104.984708),
    'Memphis, TN': (35.1491381, -90.0489803),
    'San Francisco, CA': (37.7749295, -122.4194155),
    'Houston, TX': (29.7593887, -95.362453),
    'Atlanta, GA': (33.7489924, -84.3902644),
    'New York, NY': (40.7127281, -74.0060152),
    'Charlotte, NC': (35.2272086, -80.8430835),
    'Miami, FL': (25.7616798, -80.1917902),
    'Seattle, WA': (47.6038321, -122.3300624),
    'Dallas, TX': (32.7762713, -96.7968559),
    'Columbus, OH': (39.9611755, -82.9987942),
    'Phoenix, AZ': (33.4483771, -112.0740373),
    'St. Louis, MO': (38.627003, -90.199402)
}

# ... STATUS_ORDER and STATUS_DESCRIPTIONS ...

def get_status_color(status, current_status):
    """
    Determines the color of the status dot based on the current status.

    Args:
        status (str): The status being checked.
        current_status (str): The current status of the order.

    Returns:
        str: The color of the status dot ('blue', 'black', or 'gray').
    """
    if status == current_status:
        return "#3781ad"
    elif STATUS_ORDER.index(status) < STATUS_ORDER.index(current_status):
        return "black"
    else:
        return "gray"
 
 
 # Get URL query parameters
query_params = st.query_params
customer_id = query_params.get("customer_id")

# Determine default order based on customer ID
default_order = None
if customer_id == "CUST-0001":
    default_order = "ORD-0052"
elif customer_id == "CUST-0002":
    default_order = "ORD-0013"
elif customer_id == "CUST-0003":
    default_order = "ORD-0026"

###############################################################################
# 2. Container for Search Input and Columns (set to same width)
###############################################################################

# Title & Search Input
col1, col2 = st.columns([1, 2])  # Adjust the ratios as needed

with col1:
    # Use the default order if available, otherwise an empty string
    default_search_value = default_order if default_order else ""
    search_value = st.text_input("Enter Order ID (e.g., ORD-1234):", value=default_search_value)
    order_number = search_value  # Use the search bar value as the order number


###############################################################################
# 3. Helper: Geocode a Location String
###############################################################################
def get_coordinates_from_dict(location_str):
    """
    Returns latitude and longitude for a given location string from a predefined dictionary.

    Args:
        location_str (str): The name of the city or location.

    Returns:
        tuple: A tuple containing (latitude, longitude) if found, otherwise (None, None).
    """
    if location_str in KNOWN_CITIES:
        return KNOWN_CITIES[location_str]
    else:
        return None, None

###############################################################################
# 4. Data Query from Snowflake
###############################################################################

if order_number:  # Ensures query runs ONLY when an order number is provided
    is_order = order_number.upper().startswith("ORD-")
    session = None
    session = get_snowflake_session()
    if session:
        order_product_query = f"""
            SELECT o.ORDER_ID, o.CUSTOMER_ID, o.ORDER_STATUS, o.ORDER_DATE, c.CUSTOMER_NAME,
                    s.SHIPMENT_STATUS, s.TRACKING_NUMBER,
                    'New York, NY' AS LOCATION,
                    o.EXPECTED_DELIVERY_DATE, o.ACTUAL_DELIVERY_DATE,
                    oli.PRODUCT_ID
            FROM Orders o
            JOIN Customers c ON o.CUSTOMER_ID = c.CUSTOMER_ID
            LEFT JOIN Shipments s ON o.ORDER_ID = s.ORDER_ID
            JOIN ORDER_LINE_ITEMS oli ON o.ORDER_ID = oli.ORDER_ID
            WHERE o.ORDER_ID = '{order_number}'
        """
        order_product_df = session.sql(order_product_query).to_pandas()

        if not order_product_df.empty:
            order_id = order_product_df["ORDER_ID"].iloc[0]
            order_status = order_product_df["ORDER_STATUS"].iloc[0]
            order_date = order_product_df["ORDER_DATE"].iloc[0]
            customer_name = order_product_df["CUSTOMER_NAME"].iloc[0]
            tracking_number = order_product_df["TRACKING_NUMBER"].iloc[0]
            shipment_status = order_product_df["SHIPMENT_STATUS"].iloc[0] or "Order Placed"
            location_str = order_product_df["LOCATION"].iloc[0]
            exp_delivery = order_product_df["EXPECTED_DELIVERY_DATE"].iloc[0]
            act_delivery = order_product_df["ACTUAL_DELIVERY_DATE"].iloc[0]
            product_ids = order_product_df["PRODUCT_ID"].unique().tolist()

            if order_status.lower() == "backordered":
                products_data = []
                for product_id in product_ids:
                    products_query = f"""
                        SELECT PRODUCT_NAME, PRODUCT_DESCRIPTION, PRICE, STOCK_QUANTITY
                        FROM PRODUCTS
                        WHERE PRODUCT_ID = '{product_id}'
                    """
                    product_df = session.sql(products_query).to_pandas()
                    if not product_df.empty:
                        products_data.append({
                            "name": product_df["PRODUCT_NAME"].iloc[0],
                            "subtitle": product_df["PRODUCT_DESCRIPTION"].iloc[0],
                            "price": f"${product_df['PRICE'].iloc[0]:.2f}",
                            "availability": f"{int(product_df['STOCK_QUANTITY'].iloc[0])} in Stock" if product_df["STOCK_QUANTITY"].iloc[0] > 0 else "0 in Stock",
                            "in_stock": product_df["STOCK_QUANTITY"].iloc[0] > 0
                        })
         
                # Create four columns for the backordered information with adjusted widths
                col1, col2, col3, col4 = st.columns([0.8, 1.5, 1.5, 1.3]) # Increased width for col3
                dark_gray_color = "#737373" # Define a dark gray color

                if products_data:
                    product = products_data[0] # Assuming one product for now, adjust if multiple
                    with col1:
                        st.markdown(
                            f"""
                            <div style="background-color: #ef6658; color: white; padding: 8px 14px; border-radius: 4px; width: fit-content; text-align: center; font-size: 0.95em; font-family: 'Poppins', sans-serif; font-weight: 600;">
                                Out of Stock
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    with col2:
                        #st.markdown(f"<div style='text-align: left; font-family: 'Poppins'; font-size: 0.8em; color: {dark_gray_color}; font-weight: bold;'>{product['name']}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='text-align: left; font-size: 0.8em; color: {dark_gray_color}; font-weight: bold;'>{product['name']}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='text-align: left; font-size: 0.75em; color: {dark_gray_color}; font-family: 'Poppins', sans-serif;'>{product['subtitle']}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='text-align: left; font-size: 0.75em; color: {dark_gray_color}; font-weight: bold;'>{product['price']} / <span style='color: #ef6658;'>{'0 in Stock'}</span></div>", unsafe_allow_html=True)

                    with col3:
                        st.markdown(f"<div class='order-info-container' style='text-align: left;'> <span class='order-info-label' style='font-weight: 600;'>Order Status:</span> <span class='order-info-value'>Backordered</span></div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='order-info-container' style='text-align: left;'> <span class='order-info-label' style='font-weight: 600;'>Order Date:</span> <span class='order-info-value'>{order_date.strftime('%m/%d/%Y') if order_date is not None and isinstance(order_date, pd.Timestamp) else 'N/A'}</span></div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='order-info-container' style='text-align: left;'> <span class='order-info-label' style='font-weight: 600;'>Tracking #:</span> <span class='order-info-value'>{tracking_number}</span></div>", unsafe_allow_html=True)
                    with col4:
                        st.markdown(f"<div style='text-align: left; font-family: 'Poppins', sans-serif;'> <p style='font-size: 0.75em; font-style: italic; color: {dark_gray_color}; margin-bottom: 0;'>Estimated Delivery Date</p> <p style='font-weight: bold; font-size: 1.0em; color: #ef6658; margin-top: 0;'>{exp_delivery.strftime('%B %d') if exp_delivery is not None and isinstance(exp_delivery, pd.Timestamp) else 'N/A'}</p></div>", unsafe_allow_html=True)
                    st.markdown("<hr>", unsafe_allow_html=True)
                    #st.markdown("</div>", unsafe_allow_html=True)
        
                    # --- Display Substitute Products ---
                    st.markdown(
                        """
                        <h6 style="
                            font-size: 1.1em;
                            color: #737373;
                            text-decoration: underline;
                            margin-top: -10px;
                            margin-bottom: 10px;
                        ">Product Substitutions</h4>
                        """,
                        unsafe_allow_html=True,
                    )

                    substitutions_query = f"""
                        SELECT p.PRODUCT_NAME, p.PRODUCT_DESCRIPTION, p.PRICE, p.STOCK_QUANTITY
                        FROM PRODUCTS p
                        JOIN PRODUCT_SUBSTITUTIONS ps ON p.PRODUCT_ID = ps.SUBSTITUTE_PRODUCT_ID
                        WHERE ps.ORIGINAL_PRODUCT_ID = '{product_ids[0]}' ORDER BY SUBSTITUTION_PRIORITY
                    """
                    substitution_df = session.sql(substitutions_query).to_pandas()
                    if not substitution_df.empty:
                        # ... (rest of your substitute products UI logic using substitution_df) ...
                        # Create three columns for substitutions
                        sub_col1, sub_col2, sub_col3 = st.columns(3)
                        cols = [sub_col1, sub_col2, sub_col3]
                        blue_color = "#53a69a"  # Color from your tracking dots
                        dark_gray_color = "#555555" # Define dark gray color
                        star_color = "#efad56"
                        green_color = "#63b075"
                        red_color = "#ef6658"
                        atrium_blue_color ="#3781ad"
                        black_color = "#333333"

                        original_product = next((p for p in products_data if p['name'] == product['name']), None)
                        original_product_price = float(original_product['price'].replace('$', '')) if original_product else 0  # Extract price as float

                        for i, sub_row in substitution_df.iterrows():
                            product_name = sub_row['PRODUCT_NAME']
                            product_description = sub_row['PRODUCT_DESCRIPTION']
                            substitute_price = float(sub_row['PRICE'])
                            stock_quantity = sub_row['STOCK_QUANTITY']
                            price_formatted = f"${substitute_price:.2f}"

                            # Hardcoded values for demonstration - Replace with your logic later
                            substitution_choice_options = ["Top Substitution Choice", "Secondary Substitution","Ready to Ship"]
                            substitution_choice_colors = [green_color, green_color, green_color]
                            shipping_status_options = ["Ready to Ship", "Not Ready to Ship", "Low quantity available"]
                            shipping_status_colors = [green_color, red_color, red_color]
                            review_counts = [455, 222, 311]
                            star_counts = [5, 4, 4]
                            delivery_dates = ["April 10", "April 14", "April 12"]

                            col = cols[i % 3]  # Cycle through columns

                            # Calculate the cost change
                            cost_change_value = original_product_price - substitute_price
                            cost_change_text = f"Cost {'reduction' if cost_change_value > 0 else 'increase'} of ${abs(cost_change_value):.2f}"
                            cost_change_color = green_color if cost_change_value >= 0 else red_color

                            substitution_choice = substitution_choice_options[i % len(substitution_choice_options)]
                            substitution_choice_color = substitution_choice_colors[i % len(substitution_choice_colors)]
                            shipping_status = shipping_status_options[i % len(shipping_status_options)]
                            shipping_status_color = shipping_status_colors[i % len(shipping_status_colors)]
                            review_count = review_counts[i % len(review_counts)]
                            star_count = star_counts[i % len(star_counts)]
                            delivery_date = delivery_dates[i % len(delivery_dates)]

                            with col:
                                st.markdown(
                                    f"""
                                        <div class="substitution-item" style="border: 1px solid #ccc; border-radius: 15px; padding: 10px; margin-bottom: 10px; display: flex; flex-direction: column; height: 100%;">
                                            <div class="blue-box" style="background-color: {blue_color}; color: white; padding: 8px; border-radius: 10px; text-align: left; margin-bottom: 6px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between;">
                                                <div>
                                                    <b style="font-size: .95em; font-weight: 600; color: white; margin-bottom: 0px;">{product_name}</b>
                                                    <p style="font-size: 0.75em; color: white; margin-bottom: 0px; line-height: 1.0;">{product_description}</p>
                                                </div>
                                                <b style="font-size: 0.75em; color: white; font-weight: 600; margin-bottom: 0px;">{price_formatted} per unit / {stock_quantity} in Stock</b>
                                            </div>
                                            <div class="white-box" style="padding: 0 10px; display: flex; flex-direction: column; flex-grow: 1; justify-content: space-between;">
                                                <div>
                                                    <div style="display: flex; align-items: center; margin-bottom: 5px;">
                                                        <div style="width: 10px; height: 10px; border-radius: 50%; background-color: {substitution_choice_color}; margin-right: 5px; font-size: 0.8em; line-height: 1; aspect-ratio: 1;"></div>
                                                        <p style="font-size: 0.8em; color: {black_color}; margin-bottom: 0;">{substitution_choice}</p>
                                                    </div>
                                                    <div style="display: flex; align-items: center; margin-bottom: 5px;">
                                                        <div style="width: 10px; height: 10px; border-radius: 50%; background-color: {cost_change_color}; margin-right: 5px; font-size: 0.8em; line-height: 1; aspect-ratio: 1;"></div>
                                                        <p style="font-size: 0.8em; color: {black_color}; margin-bottom: 0; line-height: 1.1;">{cost_change_text} per unit</p>
                                                    </div>
                                                    <div style="display: flex; align-items: center; margin-bottom: 5px;">
                                                        <div style="width: 10px; height: 10px; border-radius: 50%; background-color: {shipping_status_color}; margin-right: 5px; font-size: 0.8em; line-height: 1; aspect-ratio: 1;"></div>
                                                        <p style="font-size: 0.8em; color: {black_color}; margin-bottom: 0;">{shipping_status}</p>
                                                    </div>
                                                    <br>
                                                    <div style="display: flex; align-items: center; margin-top: 10px; margin-bottom: 5px;">
                                                        <p style="font-size: 0.8em; color: {black_color}; margin-bottom: 0;"><span style="font-weight: bold;">Reviews ({review_count})</span></p>
                                                        <span style="color: {star_color};">{'★' * star_count}</span>
                                                    </div>
                                                </div>
                                                <div style="text-align: center;">
                                                    <p style="font-size: 0.75em; font-style: italic; color: {black_color}; margin-top: 6; margin-bottom: 0;">Estimated Delivery Date</p>
                                                    <p style="font-weight: bold; font-size: 1.2em; color: {atrium_blue_color}; margin-top: 0; margin-bottom: 10px;">{delivery_date}</p>
                                                    <button style="background-color: #2c3143; color: white; font-size: 12px; font-weight: 600; border: none; padding: 12px 24px; border-radius: 20px; cursor: pointer;">Order</button>
                                                </div>
                                            </div>
                                        </div>
                                        """,
                                    unsafe_allow_html=True,
                                )

                        pass
                    else:
                        st.info("No substitute products found.")
            
            ######## SHipped ###############
            else:
                track_query = f"""
                    SELECT t.STATUS_UPDATE, t.LOCATION, t.TIMESTAMP, t.TRACKING_NUMBER
                    FROM Tracking t
                    JOIN Shipments s ON t.SHIPMENT_ID = s.SHIPMENT_ID
                    WHERE s.ORDER_ID = '{order_id}'
                    ORDER BY t.TIMESTAMP ASC
                """
                track_df = session.sql(track_query).to_pandas()
                left_col, right_col = st.columns([2.5, 2])
                # ... (rest of your tracking information UI logic using track_df) ...
                with left_col:
                    if not track_df.empty:
                        tracking_number = track_df['TRACKING_NUMBER'].iloc[-1]
                        st.markdown(f"<span style='font-size: 1.5em; color: #2c3143; font-weight: bold;'>Tracking # {tracking_number}</span>", unsafe_allow_html=True)

                        latest_location = track_df['LOCATION'].iloc[-1]  # Get latest location
                        lat, lon = get_coordinates_from_dict(latest_location)  # Geocode the location

                        if lat and lon:
                            # Replace st.map with a full-color interactive map using PyDeck
                            view_state = pdk.ViewState(latitude=lat, longitude=lon, zoom=11, pitch=0)
                            scatter_layer = pdk.Layer(
                                "ScatterplotLayer",
                                data=pd.DataFrame({"lat": [lat], "lon": [lon]}),
                                get_position='[lon, lat]',
                                get_radius=250,
                                get_color='[235, 0, 0, 235]',  # Blue color with transparency
                                pickable=True,
                            )
                            deck = pdk.Deck(
                                initial_view_state=view_state,
                                layers=[scatter_layer],
                                map_style="mapbox://styles/mapbox/streets-v11",
                            )
                            st.pydeck_chart(deck)
                        else:
                            st.warning(f"Could not geocode location: {latest_location}")
                    else:
                        st.markdown("Tracking number not available.")
                        st.info("No tracking data available.")

                    # Invoice, Contact, Report buttons
                    st.markdown(
                        """
                        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px;">
                            <button style="background-color: #2c3143; color: white; font-size: 14px; font-weight: 600; border: none; padding: 6px 12px; border-radius: 20px; cursor: pointer; width: 100%; box-sizing: border-box;">Invoice</button>
                            <button style="background-color: #2c3143; color: white; font-size: 14px; font-weight: 600; border: none; padding: 6px 12px; border-radius: 20px; cursor: pointer; width: 100%; box-sizing: border-box;">Contact</button>
                            <button style="background-color: #2c3143; color: white; font-size: 14px; font-weight: 600; border: none; padding: 6px 11px; border-radius: 20px; cursor: pointer; width: 100%; box-sizing: border-box;">Report</button>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with right_col:
                    st.markdown(f"<span style='font-size: 1.5em; color: #2c3143; font-weight: bold;'> </span>", unsafe_allow_html=True)
                    st.write("")
                    st.write("")
                    if not track_df.empty:
                        latest_timestamp = track_df['TIMESTAMP'].iloc[-1]  # Get latest timestamp
                        current_status = track_df['STATUS_UPDATE'].iloc[-1]  # Get latest status

                        # Format the timestamp
                        formatted_timestamp = latest_timestamp.strftime("%m/%d/%Y %I:%M%p EST") if isinstance(latest_timestamp, datetime.datetime) else "Timestamp not available"
                    else:
                        formatted_timestamp = "Timestamp not available"
                        current_status = shipment_status if shipment_status else "Label Created"

                    if not track_df.empty:
                        current_status = track_df['STATUS_UPDATE'].iloc[-1]  # Get latest tracking status
                    else:
                        current_status = shipment_status if shipment_status else "Label Created"

                    for i, status in enumerate(STATUS_ORDER):
                        color = get_status_color(status, current_status)
                        description = STATUS_DESCRIPTIONS.get(status, "No description available.")
                        text_color = "#2c3143"  # Default text color
                        dot_color = "gray"  # Default dot color (light gray)
                        line_color = "gray"  # Default line color (light gray)

                        if status == current_status:
                            text_color = "#3781ad"  # Blue for current status text
                            dot_color = "#3781ad"  # Blue for current status dot
                            line_color = "#3781ad"  # Blue for current line
                        elif color == "black":
                            dot_color = "#3781ad"  # Blue for past status dot
                            line_color = "#3781ad"  # Blue for past line
                        else:
                            text_color = "gray"  # Light gray for not occurred status titles

                        description_color = "gray"  # Light gray for description

                        # Get location and timestamp for the current status
                        location = None
                        timestamp = None
                        if not track_df.empty:
                            status_rows = track_df[track_df['STATUS_UPDATE'] == status]
                            if not status_rows.empty:
                                location = status_rows['LOCATION'].iloc[0]
                                timestamp = status_rows['TIMESTAMP'].iloc[0]

                        # Format timestamp
                        formatted_timestamp_status = ""
                        if timestamp:
                            formatted_timestamp_status = timestamp.strftime("%m/%d/%Y %I:%M%p EST") if isinstance(timestamp, datetime.datetime) else "Timestamp not available"

                        # Determine whether to show location or description
                        if color == "gray":
                            display_text = description
                        elif location:
                            display_text = f"{location} - {formatted_timestamp_status}"
                        else:
                            display_text = description

                        # Build the HTML for the status item
                        if i < len(STATUS_ORDER) - 1:
                            status_html = f"""
                                <div style="position: relative; display: flex; align-items: flex-start; margin-bottom: 10px;">
                                    <div style="width: 10px; height: 10px; border-radius: 50%; background-color: {dot_color}; margin-right: 15px; margin-top: 5px; position: relative; z-index: 1;"></div>
                                    <div style="position: absolute; top: 10px; left: 4px; width: 2px; height: calc(100% + 5px); background-color: {line_color}; z-index: 0;"></div>
                                    <div>
                                        <div style="font-weight: bold; color: {text_color};">{status}</div>
                                        <div style="font-size: 0.9em; color: {description_color};">{display_text}</div>
                                    </div>
                                </div>
                                """
                        else:
                            status_html = f"""
                                <div style="position: relative; display: flex; align-items: flex-start; margin-bottom: 10px;">
                                    <div style="width: 10px; height: 10px; border-radius: 50%; background-color: {dot_color}; margin-right: 15px; margin-top: 5px; position: relative; z-index: 1;"></div>
                                    <div>
                                        <div style="font-weight: bold; color: {text_color};">{status}</div>
                                        <div style="font-size: 0.9em; color: {description_color};">{display_text}</div>
                                    </div>
                                </div>
                                """

                        st.markdown(status_html, unsafe_allow_html=True)

                    st.write("")

        else:
            st.error("No matching order found.")

   

else:
    #st.error("Please enter an order number.")
    logger.info(f"No Order Number Entered")
