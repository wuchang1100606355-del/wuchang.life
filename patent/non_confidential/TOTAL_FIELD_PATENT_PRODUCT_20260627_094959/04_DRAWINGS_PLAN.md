# Drawings Plan

## Fig. 1 System overview
User / Browser / Local translator / API broker / Cloud candidate / Total Field / Branch field / POS / Voice / UI.

## Fig. 2 8D packet structure
D1 Intent, D2 State, D3 Coordinate, D4 Evidence, D5 Execution, D6 Generative Transmission, D7 Risk, D8 Envelope.

## Fig. 3 Dual-lane runtime
Model lane when API is allowed; lookup lane when API is unavailable.

## Fig. 4 Total Field irrigation
Candidate packet -> quarantine -> verifier -> seal -> capability table -> branch release.

## Fig. 5 Branch reconstruction
Release manifest -> lookup tables -> semantic IR -> template -> UI/voice/POS draft.

## Fig. 6 Feedback improvement loop
Output -> feedback packet -> patch candidate -> regression -> seal -> release.
