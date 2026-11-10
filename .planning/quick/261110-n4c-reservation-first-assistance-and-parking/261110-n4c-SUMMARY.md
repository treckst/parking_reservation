# Reservation-first assistance and parking information

Commit: bed5085.

The chatbot's role now prioritizes parking reservations and parking information.
The structured intent schema adds conversation: greetings, general help and
capability questions bypass retrieval and booking writes. Fresh help invites a
location and interval; help with a partial draft asks only for missing fields.
The normal English/privacy checks and final response guard still apply.

Parking information uses grounded retrieval, including questions about locations,
hours, pricing, access and rules. Insufficient evidence no longer redirects to
"another parking policy question". Unsupported/blocked messages retain limits
while explaining the assistant's actual purpose. Existing reservation collection,
date normalization, approval and overlap protection are unchanged.

Updated the web introduction, message label, example and footer to offer parking
reservations and information instead of claiming bookings are coming later.

Validation: 119 Python tests passed, 3 opt-in deployed tests skipped; 3 JS
controller tests passed. New graph tests cover generic help, existing draft
continuation, preserved evidence/history, guarded inputs and unknown parking facts.

Deployment: rebuilt graph/API images and updated Compose; all five services are
healthy. Configured-model smoke check passed the exact 'can you help?' message,
which now offers a parking reservation or parking information and asks where/when.
The same thread then answered an Airport information question with citations and
collected a reservation interval, asking for spot ID, first name, surname and
vehicle plate. It retained evidence and all six conversation messages. No booking
was created. Served HTML has the updated reservation-first wording.
