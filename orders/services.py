import os
from io import BytesIO
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.core.files.base import ContentFile

from orders.models import Orders, OrderItem, Bill
from cart.services import calculate_totals

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def create_order(user, cart, checkout_data, delivery_eta_dt=None):
    """
    Server-side order creation.
    Re-validates totals using cart.services.calculate_totals(), creates snapshot Orders,
    OrderItems, clears cart & session ETA, and updates user.has_used_first_order_discount.
    """
    totals = calculate_totals(cart)
    cart_items = cart.items.select_related("product").all()

    if not cart_items.exists():
        raise ValueError("Cannot place an order with an empty cart.")

    if not delivery_eta_dt:
        delivery_eta_dt = timezone.now() + timedelta(hours=1, minutes=30)

    # Address coordinates default to 0.0 for stub input (updated when Places API is connected)
    address_lat = Decimal(str(checkout_data.get("address_lat", "0.000000")))
    address_lng = Decimal(str(checkout_data.get("address_lng", "0.000000")))

    order = Orders.objects.create(
        user=user,
        status="completed",  # Marked completed on purchase per spec
        payment_method=checkout_data.get("payment_method", "UPI"),
        subtotal=totals["subtotal"],
        discount_amount=totals["discount_amount"],
        delivery_charge=totals["delivery_charge"],
        total_amount=totals["total_amount"],
        receiver_name=checkout_data.get("receiver_name"),
        formatted_address=checkout_data.get("formatted_address"),
        address_lat=address_lat,
        address_lng=address_lng,
        user_mobile=user.mobile_number,
        receiver_mobile=checkout_data.get("receiver_mobile"),
        delivery_eta=delivery_eta_dt,
    )

    # Snapshot OrderItems and decrement stock_qty
    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            product_name_snapshot=item.product.name,
            quantity=item.quantity,
            price_at_purchase=item.product.price,
        )
        prod = item.product
        prod.stock_qty = max(0, prod.stock_qty - item.quantity)
        prod.save(update_fields=["stock_qty"])
        try:
            from adminpanel.services import check_product_notifications
            check_product_notifications(prod)
        except Exception:
            pass

    # Mark first order discount used on user
    if totals["discount_amount"] > 0 and not user.has_used_first_order_discount:
        user.has_used_first_order_discount = True
        user.save(update_fields=["has_used_first_order_discount"])

    # Clear cart items
    cart.items.all().delete()

    return order


def generate_bill(order):
    """
    Generates a PDF bill for an Order using ReportLab and attaches it to the Bill model.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'BillTitle',
        parent=styles['Heading1'],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#007bff"),
        spaceAfter=6,
    )
    normal_style = styles['Normal']
    bold_style = ParagraphStyle('BoldText', parent=styles['Normal'], fontName='Helvetica-Bold')

    # Header
    story.append(Paragraph("Smart Inventory — Tax Invoice / Bill", title_style))
    story.append(Paragraph(f"<b>Order ID:</b> #{order.id} | <b>Date:</b> {order.placed_at.strftime('%B %d, %Y at %I:%M %p')}", normal_style))
    story.append(Paragraph(f"<b>Payment Method:</b> {order.payment_method} | <b>Status:</b> {order.get_status_display()}", normal_style))
    story.append(Spacer(1, 12))

    # Customer & Delivery Details
    cust_info = [
        [Paragraph("<b>Customer Details</b>", bold_style), Paragraph("<b>Delivery Details</b>", bold_style)],
        [
            Paragraph(f"Name: {order.user.username}<br/>Mobile: {order.user_mobile}", normal_style),
            Paragraph(f"Receiver: {order.receiver_name}<br/>Mobile: {order.receiver_mobile}<br/>Address: {order.formatted_address}", normal_style),
        ]
    ]
    t_cust = Table(cust_info, colWidths=[270, 270])
    t_cust.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8f9fa")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e9ecef")),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_cust)
    story.append(Spacer(1, 16))

    # Product Items Table
    table_data = [["Product Name", "Price (INR)", "Quantity", "Line Total (INR)"]]
    for item in order.items.all():
        line_total = item.price_at_purchase * item.quantity
        table_data.append([
            item.product_name_snapshot,
            f"₹{item.price_at_purchase:.2f}",
            str(item.quantity),
            f"₹{line_total:.2f}"
        ])

    t_items = Table(table_data, colWidths=[240, 100, 80, 120])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#007bff")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 14))

    # Summary Totals
    delivery_str = "FREE" if order.delivery_charge == 0 else f"₹{order.delivery_charge:.2f}"
    discount_str = f"-₹{order.discount_amount:.2f}" if order.discount_amount > 0 else "₹0.00"

    summary_data = [
        ["Subtotal:", f"₹{order.subtotal:.2f}"],
        ["Discount Applied:", discount_str],
        ["Delivery Charge:", delivery_str],
        ["Net Total:", f"₹{order.total_amount:.2f}"],
    ]
    t_summary = Table(summary_data, colWidths=[420, 120])
    t_summary.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor("#28a745")),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor("#333333")),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_summary)

    # Build PDF
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    # Save to Bill model
    bill, _ = Bill.objects.get_or_create(order=order)
    filename = f"bill_order_{order.id}.pdf"
    bill.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)

    return bill
