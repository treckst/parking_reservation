"""One-off fictional RAG corpus generator. Requires reportlab; run directly."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak


output = Path(__file__).with_name("pdfs")
output.mkdir(exist_ok=True)
documents = []
facilities = [
    ("CTR", "Central Courtyard", "14 Example Square, Warsaw", "central business district",
     "Example Square eastbound service lane", "the courtyard arch beside building 14",
     "A pedestrian gate leads onto Example Square. The office district is a five-minute walk away.", 8),
    ("RIV", "Riverside Yard", "28 Sample Quay, Warsaw", "riverside district",
     "Sample Quay northbound access road", "the blue entrance gate opposite warehouse 28",
     "The pedestrian exit joins the riverside walkway. The nearest bus stop is a seven-minute walk away.", 6),
    ("STA", "Station East", "6 Demo Station Road, Warsaw", "railway station district",
     "Demo Station Road from its eastern end", "the signed surface lot behind building 6",
     "The marked footpath reaches the fictional station east entrance in six minutes. Do not cross the service tracks.", 7),
    ("AIR", "Airport Approach", "42 Test Aviation Lane, Warsaw", "airport business district",
     "Test Aviation Lane via the business park junction", "the orange barrier beside reception 42",
     "This is an off-airport mock facility. No terminal shuttle is provided; arrange onward transport separately.", 5),
]
for code, name, address, area, approach, landmark, walking, base in facilities:
    documents.append((f"facility_{code.lower()}.pdf", f"{name} - facility guide", [
        ("Location and arrival", [
            ("Facility identity", f"Northgate Parking operates {name}, facility code {code}, in the {area}. The fictional address is {address}. Use facility code {code} when contacting support or checking a reservation. All addresses and facilities in this corpus are invented for testing."),
            ("Vehicle entrance", f"Approach using {approach}. Look for {landmark}. The vehicle entrance and exit share a barrier lane; arriving drivers yield to exiting vehicles. A reservation for another Northgate facility does not open this barrier."),
            ("Opening hours", "Vehicle entry and exit are available daily from 06:00 until 22:00 throughout November 2026, including weekends and November 1 and 11. Bookings must start at or after 06:00 and end by 22:00 on the same day. Overnight parking is not offered."),
            ("Walking connections", walking),
        ]),
        ("Spaces, prices and vehicle limits", [
            ("Space inventory", f"{name} has 12 numbered spaces: {code}-001 to {code}-006 are standard; {code}-007 and {code}-008 are electric; {code}-009 and {code}-010 are accessible; {code}-011 and {code}-012 are van spaces. Space identifiers are unique across facilities."),
            ("Hourly parking prices", f"Standard and accessible spaces cost PLN {base:.2f} per hour. Electric and van spaces cost PLN {base + 2:.2f} per hour. These are final mock prices with taxes included. Charging energy is separate from the electric-space parking price. There is no daily cap or overnight rate."),
            ("Dimensions and clearance", "Standard and electric vehicles may be at most 5.0 m long, 2.0 m wide and 2.0 m high. Accessible spaces allow 5.0 m length, 2.1 m width and 2.0 m height. Van spaces allow 6.0 m length, 2.2 m width and 2.8 m height. Width includes mirrors; height includes roof attachments. Maximum gross vehicle mass is 3,500 kg in every space."),
            ("On-site equipment", "The surface lot has lighting, marked pedestrian routes, an entrance intercom and two 11 kW Type 2 AC charging sockets. Bring a compatible charging cable. Accessible spaces have a marked transfer aisle that must remain clear. There is no staffed vehicle storage or luggage service."),
        ]),
        ("Using your booking", [
            ("Entry and identification", f"Check that your confirmation names {name} and the correct registration plate. At the barrier, present the booking QR code or use the intercom with the reservation ID. Follow signs to your assigned space. A QR code is valid only during the reserved interval."),
            ("If the space is occupied", "Stop in the signed waiting area and contact support using the intercom. Do not take an accessible or electric space as a substitute. Support may offer an equivalent space at the same facility; a relocation requires confirmation before you move."),
            ("Departure and delays", "Leave the assigned space and exit before the reservation end time. Request any extension before the original end time; approval depends on the next booking and the 22:00 closure. There is no automatic extension or free overstay period."),
            ("Support and related policies", f"For mock customer support use help@northgate.example, quoting facility {code}, your reservation ID and the issue. Support hours are 06:00-22:00 daily. For details consult Booking policy, Cancellation and refunds, Vehicle size rules, and Entry, exit and site safety. In an immediate emergency, contact local emergency services first."),
        ]),
    ]))

documents.extend([
    ("terms_of_service.pdf", "Terms of service", [
        ("Service and agreement", [
            ("Operator and scope", "Northgate Parking is a fictional operator used for software demonstrations. These mock terms apply to Central Courtyard (CTR), Riverside Yard (RIV), Station East (STA), and Airport Approach (AIR), for parking dates November 1-30, 2026. They are sample content, not a statement of actual law or an offer by a real business."),
            ("What a booking provides", "A confirmed reservation grants use of the identified parking space for its stated start and end times. It does not provide custody of the vehicle, a valet service, insurance, storage of goods, or permission to stay overnight. Keep the confirmation available until departure."),
            ("Customer information", "Provide a name, surname, registration plate and accurate booking interval. The driver must be authorized to use the vehicle. Correct a plate error before entry through the booking service or support. A booking applies to one vehicle at a time."),
        ]),
        ("Responsibilities and restrictions", [
            ("Customer responsibilities", "Choose a space type that fits the vehicle and comply with the posted route and 10 km/h site speed limit. Lock the vehicle, keep valuables out of view and supervise children. Keep access aisles, charging equipment and emergency routes clear."),
            ("Prohibited activities", "No sleeping in vehicles, camping, vehicle sales, mechanical repairs, fuel transfer or storage of hazardous goods is permitted. No trailers, buses or vehicles above 3,500 kg gross mass are accepted. Do not connect equipment to an outlet other than a designated charging socket."),
            ("Operator responsibilities", "The operator provides the reserved space or offers an equivalent space with the customer's agreement. If no suitable replacement is available because of an operator closure or allocation error, refund the unused parking period. No alternative facility is imposed without customer agreement."),
        ]),
        ("Problems, documents and contact", [
            ("Incident reporting", "Report damage or a service problem promptly using the entrance intercom or help@northgate.example. Include the reservation ID, facility, event time and a factual description. Keep relevant photographs and receipts. Do not include payment card details in email."),
            ("Policy order", "The confirmation controls the agreed facility, space, interval and price. Facility guides describe entrances and local equipment. Booking, cancellation, vehicle and charging policies explain the corresponding service rules. All documents in this mock release use version 1.0 and the same November 2026 validity period."),
            ("Support handling", "Customer support operates daily from 06:00 to 22:00. Written complaints receive a mock target response within five business days. These example terms do not attempt to describe or remove any rights supplied by applicable law."),
        ]),
    ]),
    ("vehicle_size_rules.pdf", "Vehicle size rules", [
        ("Select the correct space", [
            ("Standard spaces", "Standard spaces are numbered 001-006 at each facility. Maximum vehicle dimensions are 5.0 m long, 2.0 m wide and 2.0 m high. Passenger cars and small SUVs are accepted only when their actual dimensions fit all three limits."),
            ("Electric spaces", "Electric spaces are numbered 007-008. The same 5.0 m length, 2.0 m width and 2.0 m height limits apply. Reserve this type for a plug-in vehicle using the charger. A large electric van must not use an electric space if it exceeds these limits."),
            ("Measurements", "Measure width including mirrors and height including roof racks, boxes, aerial fixtures and carried loads. Manufacturer dimensions without attachments are insufficient for a loaded vehicle. A reservation does not override a dimensional limit."),
        ]),
        ("Accessible spaces and vans", [
            ("Accessible spaces", "Spaces 009-010 allow up to 5.0 m length, 2.1 m width and 2.0 m height. A valid accessible parking permit must be displayed. Keep the transfer aisle empty. These spaces provide extra side access, not extra height clearance."),
            ("Van spaces", "Spaces 011-012 allow up to 6.0 m length, 2.2 m width and 2.8 m height. Small commercial vans are permitted within these limits. Van spaces do not have charging sockets or a dedicated wheelchair transfer aisle."),
            ("Mass and excluded vehicles", "All types have a maximum gross vehicle mass of 3,500 kg. Trailers, caravans, coaches, buses and articulated vehicles are excluded even if unladen. Motorcycles may reserve a standard space at the standard hourly rate; only one motor vehicle may occupy a reserved space."),
        ]),
        ("Checks and practical examples", [
            ("Before booking", "Check the complete vehicle dimensions and gross mass, then select the matching space type. If no listed type fits, do not book. Contact help@northgate.example if a measurement or access need is unclear."),
            ("Examples", "A 4.8 m long car that is 1.95 m wide and 1.8 m high fits a standard space. A 5.5 m long van that is 2.1 m wide and 2.5 m high requires a van space. A 2.9 m high van is not accepted at any Northgate facility."),
            ("Arrival mismatch", "If the arriving vehicle exceeds its booked limits, remain outside the entrance and contact support. A change to a suitable space requires availability and payment of any price difference. If the customer cancels instead, the normal cancellation timing rules apply."),
        ]),
    ]),
    ("booking_policy.pdf", "Booking policy", [
        ("Creating a reservation", [
            ("Dates and hours", "This mock release supports parking November 1-30, 2026. All times use Europe/Warsaw local time, UTC+01:00 during this period. Every facility opens daily 06:00-22:00. A reservation must begin and end on the same calendar day within these hours."),
            ("Duration and booking details", "The minimum stay is one hour. Book whole hours with start and end times on the hour. Supply name, surname and vehicle registration plate, then choose the facility, space type and interval. Same-day bookings are permitted before their start time."),
            ("Confirmation", "A reservation is confirmed after the booking service accepts the allocation and payment. Keep the reservation ID, assigned spot ID and entry QR code. A search result or an available-space flag alone is not a confirmation."),
        ]),
        ("Availability and changes", [
            ("Checking an interval", "A space can host several reservations on the same day if their time intervals do not overlap. A booking ending at 11:00 does not conflict with another starting at 11:00. Cancelled reservations do not block the space. An available indicator does not guarantee every hour of that day is free."),
            ("Changing a booking", "Before the booked start time, request a new interval or facility through the booking service. A change is accepted only after availability and the revised price are confirmed. The original reservation remains valid until the change is accepted. Space upgrades require payment of the difference."),
            ("Extending a stay", "Request an extension before the existing end time. Extensions must be whole hours, must not overlap another booking and must end by 22:00. If rejected, leave by the existing end time. Arriving late does not move the booked end time."),
        ]),
        ("Statuses and November sample records", [
            ("Reservation statuses", "Confirmed means a non-cancelled reservation has not started. Active means its time interval includes the snapshot time. Completed means its end time has passed. Cancelled means the reservation was withdrawn and no longer holds the space. These sample statuses describe scheduling, not observed vehicle entry."),
            ("Dataset snapshot", "The companion database is a fixed snapshot at November 9, 2026, 12:00 local time. Reservation start and end dates cover November 1-10 only. Daily transport-slot records cover November 1-30. The absence of reservations after November 10 is an intentional sample-data boundary."),
            ("Current availability", "Each transport-slot row describes one spot on one date. Past dates are unavailable for new bookings. On November 9, spots with an active reservation at noon are marked unavailable. Future dates are marked available but callers must also check interval conflicts. The database does not refresh as the clock advances."),
        ]),
    ]),
    ("cancellation_and_refunds.pdf", "Cancellation and refunds", [
        ("Customer cancellation", [
            ("At least 24 hours before start", "Cancel at least 24 hours before the booked start time for a full refund of the parking charge. Exactly 24 hours before start qualifies for the full refund. The reservation becomes cancelled and its interval is released."),
            ("Less than 24 hours before start", "Cancel before the booked start but less than 24 hours ahead for a 50 percent refund of the parking charge. At the start time or later, no customer-cancellation refund is offered under this mock policy."),
            ("How to cancel", "Use the reservation cancellation action or contact help@northgate.example with the reservation ID. Cancellation is effective when accepted and confirmed. A request to change a booking is not itself a cancellation."),
        ]),
        ("No-shows, early exits and closures", [
            ("Late arrival and no-show", "A late arrival retains the original booked end time. The space remains reserved for the full paid interval unless the reservation is cancelled. A no-show receives no refund; the sample database does not use a separate no-show status."),
            ("Early departure", "Leaving early does not automatically cancel the remaining hours and does not generate a partial refund. The customer may still use the space until the original end time, subject to the entry rules."),
            ("Operator cancellation", "If the operator cannot supply the space, support may offer an equivalent replacement with customer consent. If there is no accepted replacement, refund the unused parking period in full. A closure before the stay begins therefore results in a full parking refund."),
        ]),
        ("Refund calculation and examples", [
            ("Refund processing", "Refunds return to the original payment method. The mock processing target is five business days after acceptance; banking delays may add time. Charging energy already consumed is excluded from parking refunds. Keep the cancellation confirmation until the credit arrives."),
            ("Timing examples", "For a November 10 booking starting at 10:00, cancellation by November 9 at 10:00 earns a full parking refund. Cancellation on November 9 at 12:00 earns 50 percent. Cancellation on November 10 at 10:00 earns no customer-cancellation refund."),
            ("Amount example", "A four-hour standard booking at Central Courtyard costs PLN 32.00. Its full refund is PLN 32.00; its 50 percent refund is PLN 16.00. This example concerns parking only and assumes no separately consumed charging energy."),
        ]),
    ]),
    ("entry_exit_and_safety.pdf", "Entry, exit and site safety", [
        ("Arriving and parking", [
            ("Before reaching the barrier", "Check the facility code, vehicle plate and booking interval on the confirmation. Entry is available only during the reserved interval and within 06:00-22:00. Early arrivals must wait outside the lot without blocking public access."),
            ("Opening the barrier", "Present the confirmation QR code to the reader. If the reader fails, use the intercom and provide the reservation ID and plate. Do not follow another vehicle through an open barrier. Each vehicle must complete its own entry check."),
            ("Finding the space", "Follow the marked route at no more than 10 km/h and park wholly within the assigned bay. If another vehicle occupies it, use the waiting area and contact support. Never block an emergency route while resolving a booking problem."),
        ]),
        ("During the stay", [
            ("Pedestrian movement", "Use marked walkways and keep children close. Drivers yield to pedestrians and exiting vehicles. Accessible transfer aisles are not waiting areas, luggage zones or motorcycle spaces."),
            ("Repeat entry", "The same booked vehicle may exit and re-enter during its reserved interval. Re-entry does not extend the end time, and the reservation cannot be shared with a second vehicle. Keep the QR code private."),
            ("Incidents", "For immediate danger, move to a safe place and contact local emergency services. Notify site support once safe. Do not attempt repairs to barriers, electrical equipment or charging sockets. Report damaged equipment through the intercom."),
        ]),
        ("Departure and assistance", [
            ("Leaving on time", "Exit by the reservation end time. No grace period is guaranteed. Request a whole-hour extension before the original end time if needed; it must be confirmed and cannot run beyond 22:00."),
            ("Overstay handling", "An unapproved overstay may block the next customer. Contact support immediately; any additional parking is charged at the booked space's hourly rate per started hour. This charge does not grant permission to remain or guarantee access after closing."),
            ("Barrier failure or late exit", "Use the intercom if the exit barrier fails. If unable to leave by 22:00, contact support before closing to arrange assistance. There is no scheduled overnight access service. Never force a barrier or drive through a pedestrian gate."),
        ]),
    ]),
    ("pricing_and_payments.pdf", "Pricing and payments", [
        ("Hourly rate card", [
            ("Central Courtyard and Riverside Yard", "At Central Courtyard (CTR), standard and accessible spaces cost PLN 8.00 per hour; electric and van spaces cost PLN 10.00. At Riverside Yard (RIV), standard and accessible spaces cost PLN 6.00; electric and van spaces cost PLN 8.00."),
            ("Station East and Airport Approach", "At Station East (STA), standard and accessible spaces cost PLN 7.00 per hour; electric and van spaces cost PLN 9.00. At Airport Approach (AIR), standard and accessible spaces cost PLN 5.00; electric and van spaces cost PLN 7.00."),
            ("Validity and currency", "These final mock prices include taxes and apply daily throughout November 1-30, 2026. Prices are in Polish zloty (PLN). There is no weekend surcharge, holiday surcharge, daily cap, membership discount or overnight product."),
        ]),
        ("Calculating the charge", [
            ("Booked parking", "The parking charge is the hourly rate multiplied by the number of booked whole hours. The minimum stay is one hour. A three-hour standard visit at Station East costs PLN 21.00. A four-hour van visit at Airport Approach costs PLN 28.00."),
            ("Electric charging", "Electric-space parking is charged at its listed hourly rate whether charging is continuous or intermittent. Consumed energy costs an additional PLN 1.80 per kWh, measured by the charger. Energy use is not included in the parking database's hourly_price field."),
            ("Changes and additional time", "A confirmed extension uses the same space's hourly price. Changing facility or space type recalculates the price for the accepted replacement. Unapproved overstays are charged per started extra hour but do not create a right to stay."),
        ]),
        ("Payment and receipts", [
            ("Payment confirmation", "The mock booking service accepts card payment before confirming a reservation. No cash collection is offered at the barrier. A declined or abandoned payment does not confirm a space; retry through the booking service."),
            ("Receipts and support", "Request a receipt using the reservation ID and the booking contact details. For an incorrect charge, contact help@northgate.example with the facility, booking interval and disputed amount. Never send a full card number or security code."),
            ("Sample-system limits", "The companion SQLite database stores hourly prices and reservation details but does not include payment transactions, refunds, charging sessions or billing identity. Treat the examples here as static policy facts, not evidence that a payment actually occurred."),
        ]),
    ]),
    ("electric_vehicle_charging.pdf", "Electric vehicle charging", [
        ("Equipment and eligibility", [
            ("Charging spaces", "Each Northgate facility has two electric spaces, numbered 007 and 008. Each space has an 11 kW Type 2 AC socket. Bring a compatible cable. DC rapid charging and adapters supplied by the operator are not available."),
            ("Eligible vehicles", "Electric spaces are for plug-in vehicles using the charger during their stay. Vehicles must fit the 5.0 m length, 2.0 m width and 2.0 m height limits and stay within 3,500 kg gross mass. A connector match does not override the size limits."),
            ("Power expectations", "Actual charging power depends on the vehicle, battery condition and site load. The advertised 11 kW is a maximum, not a guaranteed sustained output. No particular battery level at departure is promised."),
        ]),
        ("Starting and ending a session", [
            ("Start procedure", "Park in the assigned electric space, inspect the socket and cable for visible damage, and follow the charger's display prompts. Use the reservation reference when prompted. Keep the cable within the marked bay and out of pedestrian routes."),
            ("Finish procedure", "Stop charging using the display or vehicle control, unlock the connector and take your cable. Complete disconnection and exit before the parking reservation ends. Charging does not extend the parking interval."),
            ("A charging fault", "Stop using visibly damaged equipment and report the charger number, facility and reservation ID through the intercom. Do not dismantle a connector or reset electrical cabinets. Support can offer another compatible space only if one is available."),
        ]),
        ("Prices and service interruptions", [
            ("Separate parking and energy charges", "Parking uses the electric-space hourly rate: CTR PLN 10.00, RIV PLN 8.00, STA PLN 9.00, AIR PLN 7.00. Energy costs PLN 1.80 per kWh in addition. A two-hour CTR stay consuming 10 kWh costs PLN 20.00 parking plus PLN 18.00 energy."),
            ("Equipment unavailable on arrival", "Contact support before starting the stay if the reserved charger is unusable. Support may offer another electric space. If the customer accepts a standard space, use the standard parking rate and charge no energy. If no suitable replacement is accepted, refund the unused parking period."),
            ("Availability information", "A bookable electric parking space does not report a charger's live health. The November sample database contains no charger telemetry or energy measurements. Use support for operational faults; use the database for spot and reservation schedules."),
        ]),
    ]),
    ("accessible_parking.pdf", "Accessible parking and assistance", [
        ("Spaces and eligibility", [
            ("Reserved accessible spaces", "Every Northgate facility has two accessible spaces, numbered 009 and 010. A valid accessible parking permit must be displayed while parked. The permit holder must be travelling in the booked vehicle as driver or passenger."),
            ("Vehicle dimensions", "Accessible spaces accept vehicles up to 5.0 m long, 2.1 m wide and 2.0 m high, with maximum gross mass 3,500 kg. Width includes mirrors and height includes roof attachments. A high-roof wheelchair vehicle may exceed the height limit; confirm suitability before booking."),
            ("Rates", "Accessible spaces use the standard rate: CTR PLN 8.00, RIV PLN 6.00, STA PLN 7.00, AIR PLN 5.00 per hour. There is no accessible-space surcharge or automatic free parking entitlement in this mock service."),
        ]),
        ("Site access and assistance", [
            ("Transfer aisles and paths", "Marked side transfer aisles must remain empty. Each site has a step-free pedestrian route from its accessible spaces to the pedestrian exit. Do not leave luggage, cables or scooters in the aisle. The facility guides identify local pedestrian connections."),
            ("Requesting assistance", "Contact help@northgate.example before the visit with the facility, planned interval and practical access requirement. You do not need to send medical records or a diagnosis. Support can explain routes and entry steps but does not provide lifting or personal care."),
            ("Entrance difficulty", "If the barrier reader is difficult to reach, use the entrance intercom for assistance. Keep the reservation ID available. Do not leave a vehicle unattended in the barrier lane or attempt to enter through the pedestrian gate."),
        ]),
        ("Booking issues and alternatives", [
            ("No accessible space available", "Do not reserve a standard or van space on the assumption that a transfer aisle will be provided. Contact support to discuss another facility or time. A different space is suitable only if it meets the customer's stated access needs."),
            ("Assigned space blocked", "Wait safely and report the obstruction through the intercom. Support may offer an equivalent accessible space with customer agreement. If a suitable replacement cannot be supplied, refund the unused parking period under the operator-cancellation policy."),
            ("Charging and accessible parking", "Accessible spaces do not have charging sockets. Electric spaces do not have dedicated accessible transfer aisles. The current mock sites do not offer a combined accessible charging space; discuss requirements with support before making a reservation."),
        ]),
    ]),
])

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("DocumentTitle", fontName="Helvetica-Bold", fontSize=20, leading=25,
                          textColor=colors.HexColor("#17364b"), spaceAfter=12))
styles.add(ParagraphStyle("SectionTitle", fontName="Helvetica-Bold", fontSize=15, leading=20,
                          spaceAfter=16, textColor=colors.HexColor("#246779")))
styles.add(ParagraphStyle("Topic", fontName="Helvetica-Bold", fontSize=11, leading=15,
                          spaceBefore=12, spaceAfter=5, keepWithNext=True))
styles.add(ParagraphStyle("Text", fontName="Helvetica", fontSize=10.5, leading=16,
                          spaceAfter=10, alignment=TA_LEFT))
styles.add(ParagraphStyle("Metadata", fontName="Helvetica", fontSize=9, leading=13,
                          textColor=colors.HexColor("#52616b"), spaceAfter=14))


def page_footer(canvas, document):
    canvas.setStrokeColor(colors.HexColor("#d7e1e5"))
    canvas.line(22 * mm, 18 * mm, 188 * mm, 18 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#52616b"))
    canvas.drawString(22 * mm, 13 * mm, "Northgate Parking | Fictional mock documents | November 2026")
    canvas.drawRightString(188 * mm, 13 * mm, f"Page {document.page} of 3")


for filename, title, pages in documents:
    story = []
    for page_number, (section, topics) in enumerate(pages, start=1):
        if page_number > 1:
            story.append(PageBreak())
        story.append(Paragraph(title, styles["DocumentTitle"]))
        story.append(Paragraph("Version 1.0 | Effective November 1-30, 2026 | Fictional test content", styles["Metadata"]))
        story.append(Paragraph(f"{page_number}. {section}", styles["SectionTitle"]))
        for heading, body in topics:
            story.append(Paragraph(heading, styles["Topic"]))
            story.append(Paragraph(body, styles["Text"]))
        story.append(Spacer(1, 6 * mm))
    document = SimpleDocTemplate(
        str(output / filename), pagesize=(210 * mm, 297 * mm),
        leftMargin=22 * mm, rightMargin=22 * mm, topMargin=20 * mm, bottomMargin=25 * mm,
        title=title, author="Northgate Parking - fictional sample operator",
        subject="November 2026 parking reference material for RAG testing",
    )
    document.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    print(output / filename)
