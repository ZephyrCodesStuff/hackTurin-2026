import argparse
import os
import sys
import time
import random
import threading
from datetime import datetime, timezone
import httpx

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
DEFAULT_BASE_URL = "https://hackturin-api.zeph.work"

# Paste your new JWT token here, or pass it via --token / env var JWT_TOKEN
CAMERA_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJyb290IiwiaXNzIjoidHJhZmZpYy1jYW1lcmEtYXBpIiwiaWF0IjoxNzkxNzE5MjAwLCJleHAiOjE3OTE4MDU2MDAsImF1dGhvcml6ZWRfY2FtZXJhX2lkcyI6WyIwMmNiMzlkNC1hNGFhLTQ0ZjktOGQ1ZS0zYTE5ZDIxOTQ4MjUiLCIwYmM3ZTNmMC1iYWE4LTRiMGMtOGE3Ni1kZjY1MWQ3YWE2ZWEiLCIwZjVkNDQyOS0xYWJkLTRmNzktYTRkNC0xN2M1YTFjNmJmMmYiLCIwZmNkOWM1OC1mZmM0LTRlYzAtOThhZi0zOGE0ZTU1ZDg4ZWQiLCIxNzU3YzQ3ZC1iNDkzLTQ3M2ItYjhiOC0xMjExNmU0ZGZiMGYiLCIxZGJkNTRhZS03YWY4LTRjYTUtYTNhMC0wN2QzZjc0ZDY3ZmIiLCIyMzlkNWRlZi01MDM1LTQ5YjAtOWM0Yi1mMDY5NDUxYjQ1MmUiLCIyNTc4ZDg3Ni02Y2RkLTRlNTUtYjUyYi1mM2RjMjA4YzdlNTQiLCIyNWQzYmZhMS05MTZlLTQyNzktOWU0Mi1kYmRkMjc2MDBhY2IiLCIyNjI5NjQ5Ni1hYTUzLTQ3YzgtODFmNi1iMmE1YzY4ZTY4OGUiLCIyNzU1YTU4Ni0yY2UwLTQyYzEtYTc5NS03ZWRmNGUwZjBlMjkiLCIyODY0NjgxOS1kZjZhLTRjZjItOGZiZS04MzUxOWRhYjA0MDMiLCIyZWRjNzVjMi1mYjA0LTQxNDEtYmY0Ny1hM2M1NDE2OTQwYjMiLCIzMjI3OTdkYi1jZTZlLTQ0MWYtOWVhMS1mN2RiOTQ4ZjFmMTQiLCIzNDFjMzNhNS1jZDBlLTRiYTctYTMzMS1iYTA3MWNiNzhlNDciLCIzOTBjZjMyZC00NDZkLTQ4YzYtYjQ2OC1iZDhlMTRhZDg0M2IiLCIzYTVmNmFlZi1hNmQwLTQ0OTAtOWFiYS04YjFlOGYzODIzMjIiLCIzZDYxMDVkMS1lZmVmLTQxZjktYTE0NS0yZjBjZWM0NDZkOWYiLCIzZjIwODYyYi0wZGViLTQwMTEtYWQyNC1iOTU0ODE3NjIzMjkiLCI0MDNmMWU0Yi1mNWRlLTQ1NzMtODBlNC01MTRmM2E2NWQ4NDYiLCI0MjhiMzIzZC02ODFhLTQxZjMtOGRiZS1kMDA1YzAwZjM0ZmIiLCI0NGI3YWJkZS05YjBmLTQxN2YtOGJiMi1iYTNlN2ZmYTcyNTIiLCI0NGQ4YjE2OS0xN2Y4LTQyZDgtYjQ1OS0xZWE0N2JjNjhhOGMiLCI0ZDc5YjE4ZS0xZWZjLTQxZDYtYmE0MS0xNzE4YzIwNzNkODciLCI1MDYzMzVlMS0zNTdhLTQ4ZWItYmVlYi1kY2E1ZjEyMDcyNzciLCI1MGNjYTEzZS1iMDMyLTQzY2MtOTE5ZS1iZjg0MzkyNWYyYzEiLCI1MGNmZDZhYy1hOTU0LTRiYzEtODlmMC04NTYzYmI3Zjc0NTAiLCI1MTY1NGI5My05NDc2LTRhNWEtYWUzNi0xYTg0MWM3MzcwZGIiLCI1MmNjNjYyYS04NWNhLTQ4YmQtOGQwYS0wMDlkZDZlMjA4ZTUiLCI1Mzk5YmQxMi1kZTgyLTRjYzktYWE5Ny05ZjliMTA1YTg3ZWMiLCI1M2RkMDU5OS03ZWVkLTRhMDQtODQ3Ni02MGYzYmZhNDkxZDQiLCI1OTYyYTc0My1hMDQ0LTQwY2ItOTJlZi04YjZiMGRhMTYwZGEiLCI1OWJmYTFjNy02ZDZlLTQ5ZmEtYTVlMi1kNWJhNjY4NDRlYTEiLCI1YTk1ZjQ4ZC0xOWNhLTRkMTUtYjVkMC04NDkzNDlkNDFhM2UiLCI1ZDU0MjM4YS03OTkxLTQ3NWQtOTBiOC1hYTIzNjgzNGQ5NDEiLCI1ZTk1OWUzZC1lYjc3LTQzYWQtOWE1OC0zMzdiZDBhNjQ4NGUiLCI2MDExMjljZS1lZDI4LTQ1YWItODRhZi02NGI4YmY0MmEzYjEiLCI2NjE0NDhlYi0zNDVhLTRjZDMtODIzOS1lZWVhMWY1NjlmZWUiLCI2ZDg0MTUxMS03YTk0LTQ0OGMtYjFkNS1kNzhlM2QwODUwNjgiLCI2ZjBhZDJiMi02YjhhLTQ0NGQtOTQwOS0wYjE5ZDQ5YWY3ZmQiLCI3ODUyZmVlMy1hZWYwLTQ5ODQtOTBkZC04YTMxZjBmMWEzZTkiLCI3YmE0NGQ4MC0zOWZlLTQ5ZWUtYjNhYy05MTlmMWE2MTk1Y2QiLCI3ZTQ5NDUxNS0xZmVlLTRiZGItODdhMC1hNjM3MTFlYTNkM2UiLCI4MGRmNzE3NS03ZGNjLTRkMzQtYjE3OC01ZTQ1MzkzMzVlZjAiLCI4MmI3ZjE4Ni0zZjNmLTQzMmItYWY5NS03MDQ4YTgxYWFmZDUiLCI4NGNhN2NiNi05ZTVmLTRlNTQtYWVjMy04YWYxNmM5YzU2NmUiLCI4NGY2Y2I2OS00ZDhlLTQ5OTktOWI2Mi00ZjRmYjA1ODBjNGIiLCI4NTBmMWQ4Ny1kMWFmLTRkOTQtYWU4Mi1jOWMxMDEzNmJlNjIiLCI4NjhmYjM0Ni1kYWFjLTRkZDUtYjQyMC1hYzc3M2E1ZjVhNWIiLCI4NjlkMzBhMi0zMWM4LTRmOTAtODhmMC1kMDkyZWMxN2I1OGUiLCI4YTk0OTU3My03MTNlLTQ1OTUtYTJmNi1iM2NjNWIxNzU0NTkiLCI4YjJiZTFjMy0xYTdhLTQwOTEtYWM5Mi0zOGQxOTk5ZmEyYzQiLCI4YzRjNDYzOC04Yzc1LTQwYWYtODRlNy1hZWUzMzIxOWM0MDIiLCI4ZmMzYjgzYy04NDY1LTQyYTYtYjIyMi1lMDI0NGQyZTY0MTAiLCI4ZmQzNGRjNi1lN2NjLTRhYTYtYWFiNC0wNmYxMjU1ZWNkZTIiLCI5MGM3YTc1OC03Zjk3LTRhYWYtOTZhZi05NjNhYjU3N2Y1MmIiLCI5NTM2ZTYyOC1mODYwLTQzODUtYWNhNS1kNWNmZGI5OGE5ZjIiLCI5NjU1NWFkOC0xNGRiLTQwMjQtYTkyOS1jNTE2ZmYyZWY2NDEiLCI5NmYzNTY1OS0yNjM4LTRhNWEtYTAwNS1mYjc2OWI3YjU1NzEiLCI5NmY0NmFmNi0xODQxLTQwYzItYjJhMC00Y2VlNDE5ZDc4ZjEiLCI5ODc5ODA2OC1jODc3LTRhOGItYWIzZC1kYzg4ZGQ4NTcyZjMiLCI5OGZkNmIxMC1lYWQzLTQxYzItYTZiZC0zZWRlYjY4MzJjMjciLCJhMGQyM2QyZi03YzZjLTRjMTYtYmY0Ni1iY2RhZWJmMWJiYWEiLCJhMTY4MWRhNy1mYjRlLTQ5Y2ItYjIyOS0wMTJlZTVhNWJlOTQiLCJhM2NiM2NhOS1lYjE2LTRhOGMtYjU5ZC1lNzcwOWY1MjYzNWMiLCJhM2VmODZlYi1lNmFmLTQ5MWItYjgxMi0yZWU2MjIxNDhmNzciLCJhNTIyODlmNS1lNDAxLTRlMDQtYjVjZS1iNGZkOWJjNjJiZjciLCJhNzFjZmNkYS0zNjNjLTQ2NzQtYTc2ZS0wMmUyNjQ5NzI4YjEiLCJhYTY2M2NlZC01NzEzLTQwODUtODgyNS0wNjFlMjc3ZmFhNWMiLCJhYjM3OTgzNC02N2JiLTQ2ZWItYmExMS0wOTZhM2JlZDM0ZjAiLCJhYjNlZjNiZi04MDFlLTQ0MGQtOWFiMy1iMzQyODYwMWE3YmMiLCJhYjViMmQ3Ny01ZmU3LTQ5MmUtOGFmYS0yNjZmN2Y1M2ExMTciLCJhZDBjMTM0Ni0wNGYyLTRlMWEtOTVmNy1lZDBmZTRiYmNlZjQiLCJhZTY2NWU5Zi04ZDE0LTQ5YzktOThiOS0zZmQ4ZDI5MzA4YTMiLCJhZjdkOGRkNi00Y2RiLTQyZmEtOTgzZi0wMzcyZTM0N2RiNWYiLCJiM2UyMDJjOS1iNDM0LTQwYTctYmJiNi0yZmI0ZTU3NmFlZGIiLCJiNDkzZDljOC0zZDRlLTRkODEtOTg4YS1iZWFmMWRkZmNjMjUiLCJiNGIwYTFjZi1hNTFjLTQ2NjMtOThjZC05YmY0NzNiY2U0YTkiLCJjNGFiZDRhYi01MTM0LTQwZmEtODUxZC00NjQ5NjM3ZDMzNGEiLCJjNWJmZDNmNy03NWMwLTRjMmQtOGFhZC1iMzNhODFjYzhjMjciLCJjOTJhOTdkMi03NDEzLTQ1YjAtYTZjMS04ZTZiYjcwNmY1NjEiLCJjOTk2N2U5ZC0wZDU0LTQyMzktYmVkYy0yYjExNTEyNWVhMGMiLCJjYWI3OWMzNS0xMjg0LTQwZmUtOWQ5Yi0zYTE2NzEzZWEyNjEiLCJkMTdiMDY3ZS1lZDc4LTRiMDEtYjU2ZS05MzkyNGJmODE0OGIiLCJkMmVhMGRhNi05OGEwLTRmNzQtODhmNy0wY2Q0ODA1ZjhmYTAiLCJkMzdmZGRhOS0yMmI3LTQwMjgtYWUyOS02MzFjYTc3YTU1NjciLCJkNTljMDg2NS04ODk0LTQ0MDgtYTAyMC1lZDM1NmIyZjhkMmQiLCJkNjA1OTlmOS1hM2M5LTQ0MzctYjE4OC1lZTZkMGZiZTZiYzciLCJkYWRiMTc5OC1hMjI0LTRhNzgtYTEyMC01YjE3ZjgxZWE1ZTUiLCJkYzU4ZjU1Zi1iYTljLTQzOGYtOWExNi1iMGIxY2FjNjViNjIiLCJkY2MzM2E4NS0xM2U5LTQ4YzAtYjdmZC1iY2RhMzQyNWRkNWYiLCJkY2Y1ZWI4OC04MGE1LTQ3MDktYTk3Ni1hNDhkN2IxNzBkOGQiLCJlN2NjNGZmZi1mZmJlLTRjM2QtYTA2OS01YTA1M2IzMTU3ZjMiLCJlODVkMmE1MC0yYWVkLTRmMjUtYTMyMi1lOTA3OTMxZGQ3NDgiLCJlOGY0ZjA3Yi0zMzNhLTRiMTctYTMxMi1lMzVlZWEyNDEwZDYiLCJlYzRiN2ExZC01NmQyLTQ5NGUtYmY5Mi03MWVlMzdhMWRhODYiLCJlZGE0MmE5My04OWI2LTQzYzctYTBiMy1kMWIzMjI0NzYxNWUiLCJmMWNmMWY5Yi01ZmFiLTQ1OTktOWU3Mi02N2M5ZGM1MTZiZTUiLCJmN2YyYzUxYy03M2NjLTRkYTktYTMyNi1hYTdhNzk2ODMxZGIiLCJmN2ZjOTM0NS03ZGUyLTRhOGEtOWRkMi1iYjNmNmVhN2NmNjciXSwidHlwZSI6ImNhbWVyYV90b2tlbiJ9.z5o2wbBtboLzCL__lmrtvOig1WttRJ-9P_h59NYpMmE"
UUIDS = '0bc7e3f0-baa8-4b0c-8a76-df651d7aa6ea,4d79b18e-1efc-41d6-ba41-1718c2073d87,c4abd4ab-5134-40fa-851d-4649637d334a,02cb39d4-a4aa-44f9-8d5e-3a19d2194825,1757c47d-b493-473b-b8b8-12116e4dfb0f,84f6cb69-4d8e-4999-9b62-4f4fb0580c4b,869d30a2-31c8-4f90-88f0-d092ec17b58e,28646819-df6a-4cf2-8fbe-83519dab0403,ab379834-67bb-46eb-ba11-096a3bed34f0,98fd6b10-ead3-41c2-a6bd-3edeb6832c27,6d841511-7a94-448c-b1d5-d78e3d085068,868fb346-daac-4dd5-b420-ac773a5f5a5b,2578d876-6cdd-4e55-b52b-f3dc208c7e54,a3cb3ca9-eb16-4a8c-b59d-e7709f52635c,59bfa1c7-6d6e-49fa-a5e2-d5ba66844ea1,50cfd6ac-a954-4bc1-89f0-8563bb7f7450,d60599f9-a3c9-4437-b188-ee6d0fbe6bc7,8b2be1c3-1a7a-4091-ac92-38d1999fa2c4,aa663ced-5713-4085-8825-061e277faa5c,239d5def-5035-49b0-9c4b-f069451b452e,a3ef86eb-e6af-491b-b812-2ee622148f77,8a949573-713e-4595-a2f6-b3cc5b175459,7e494515-1fee-4bdb-87a0-a63711ea3d3e,af7d8dd6-4cdb-42fa-983f-0372e347db5f,5a95f48d-19ca-4d15-b5d0-849349d41a3e,a0d23d2f-7c6c-4c16-bf46-bcdaebf1bbaa,80df7175-7dcc-4d34-b178-5e4539335ef0,f7fc9345-7de2-4a8a-9dd2-bb3f6ea7cf67,ab3ef3bf-801e-440d-9ab3-b3428601a7bc,53dd0599-7eed-4a04-8476-60f3bfa491d4,50cca13e-b032-43cc-919e-bf843925f2c1,90c7a758-7f97-4aaf-96af-963ab577f52b,6f0ad2b2-6b8a-444d-9409-0b19d49af7fd,dc58f55f-ba9c-438f-9a16-b0b1cac65b62,601129ce-ed28-45ab-84af-64b8bf42a3b1,96555ad8-14db-4024-a929-c516ff2ef641,506335e1-357a-48eb-beeb-dca5f1207277,0f5d4429-1abd-4f79-a4d4-17c5a1c6bf2f,2755a586-2ce0-42c1-a795-7edf4e0f0e29,5d54238a-7991-475d-90b8-aa236834d941,e7cc4fff-ffbe-4c3d-a069-5a053b3157f3,428b323d-681a-41f3-8dbe-d005c00f34fb,51654b93-9476-4a5a-ae36-1a841c7370db,ae665e9f-8d14-49c9-98b9-3fd8d29308a3,b3e202c9-b434-40a7-bbb6-2fb4e576aedb,ab5b2d77-5fe7-492e-8afa-266f7f53a117,b4b0a1cf-a51c-4663-98cd-9bf473bce4a9,c5bfd3f7-75c0-4c2d-8aad-b33a81cc8c27,e8f4f07b-333a-4b17-a312-e35eea2410d6,cab79c35-1284-40fe-9d9b-3a16713ea261,e85d2a50-2aed-4f25-a322-e907931dd748,7ba44d80-39fe-49ee-b3ac-919f1a6195cd,341c33a5-cd0e-4ba7-a331-ba071cb78e47,ad0c1346-04f2-4e1a-95f7-ed0fe4bbcef4,d2ea0da6-98a0-4f74-88f7-0cd4805f8fa0,a52289f5-e401-4e04-b5ce-b4fd9bc62bf7,661448eb-345a-4cd3-8239-eeea1f569fee,98798068-c877-4a8b-ab3d-dc88dd8572f3,3f20862b-0deb-4011-ad24-b95481762329,dadb1798-a224-4a78-a120-5b17f81ea5e5,5962a743-a044-40cb-92ef-8b6b0da160da,96f46af6-1841-40c2-b2a0-4cee419d78f1,eda42a93-89b6-43c7-a0b3-d1b32247615e,dcc33a85-13e9-48c0-b7fd-bcda3425dd5f,a1681da7-fb4e-49cb-b229-012ee5a5be94,a71cfcda-363c-4674-a76e-02e2649728b1,322797db-ce6e-441f-9ea1-f7db948f1f14,d59c0865-8894-4408-a020-ed356b2f8d2d,3d6105d1-efef-41f9-a145-2f0cec446d9f,c92a97d2-7413-45b0-a6c1-8e6bb706f561,96f35659-2638-4a5a-a005-fb769b7b5571,f7f2c51c-73cc-4da9-a326-aa7a796831db,26296496-aa53-47c8-81f6-b2a5c68e688e,9536e628-f860-4385-aca5-d5cfdb98a9f2,390cf32d-446d-48c6-b468-bd8e14ad843b,403f1e4b-f5de-4573-80e4-514f3a65d846,5399bd12-de82-4cc9-aa97-9f9b105a87ec,3a5f6aef-a6d0-4490-9aba-8b1e8f382322,84ca7cb6-9e5f-4e54-aec3-8af16c9c566e,44d8b169-17f8-42d8-b459-1ea47bc68a8c,0fcd9c58-ffc4-4ec0-98af-38a4e55d88ed,44b7abde-9b0f-417f-8bb2-ba3e7ffa7252,8c4c4638-8c75-40af-84e7-aee33219c402,8fd34dc6-e7cc-4aa6-aab4-06f1255ecde2,8fc3b83c-8465-42a6-b222-e0244d2e6410,52cc662a-85ca-48bd-8d0a-009dd6e208e5,1dbd54ae-7af8-4ca5-a3a0-07d3f74d67fb,dcf5eb88-80a5-4709-a976-a48d7b170d8d,7852fee3-aef0-4984-90dd-8a31f0f1a3e9,850f1d87-d1af-4d94-ae82-c9c10136be62,f1cf1f9b-5fab-4599-9e72-67c9dc516be5,d17b067e-ed78-4b01-b56e-93924bf8148b,82b7f186-3f3f-432b-af95-7048a81aafd5,b493d9c8-3d4e-4d81-988a-beaf1ddfcc25,ec4b7a1d-56d2-494e-bf92-71ee37a1da86,c9967e9d-0d54-4239-bedc-2b115125ea0c,d37fdda9-22b7-4028-ae29-631ca77a5567,2edc75c2-fb04-4141-bf47-a3c5416940b3,25d3bfa1-916e-4279-9e42-dbdd27600acb,5e959e3d-eb77-43ad-9a58-337bd0a6484e'.split(',')

# 10 Traffic Light Cameras and their GPS Coordinates
# traffic_lights = [
#     {"uuid": "8bb8d7dc-e5bb-4a1b-91ea-c8f737e1c93b", "location": [45.0637, 7.6749]},
#     {"uuid": "c85c1b51-45e3-4aa6-9e0e-f48f6be910e4", "location": [45.0573, 7.6885]},
#     {"uuid": "59e57856-ea20-4e4a-a0c4-ace77142b132", "location": [45.0741, 7.6631]},
#     {"uuid": "84fa39e6-e6c1-47bf-b45f-8ba45faf32f6", "location": [45.0617, 7.6582]},
#     {"uuid": "7b41a1e4-25ff-4774-b808-055acdd8d30b", "location": [45.0628, 7.6644]},
#     {"uuid": "3973e990-2a5d-47b7-bb8e-3a2d33d5afc1", "location": [45.0802, 7.6748]},
#     {"uuid": "216b81d5-6280-4db0-93ae-fc4f5985d7f1", "location": [45.0834, 7.6896]},
#     {"uuid": "3219e673-0f44-46e5-bc84-020b15d0f7c7", "location": [45.0645, 7.6938]},
#     {"uuid": "7054e83a-3edf-4fd4-8b0e-8c0fbeaca955", "location": [45.0768, 7.6681]},
# ]
TRAFFIC_LIGHTS = [{'uuid':x,'location':[45.0637 + (random.randint(0, 200) - 100) / 1000, 7.6749 + (random.randint(0, 200) - 100) / 1000]} for x in UUIDS]

# The API expects light colors: 'red', 'amber', 'green'. Yellow is mapped to 'amber'.
# Cycle:
# 1. RED for 10s -> transitions to AMBER
# 2. AMBER for 3s -> transitions to GREEN
# 3. GREEN for 10s -> transitions to AMBER
# 4. AMBER for 3s -> transitions to RED
LIGHT_CYCLE = [
    {"color": "red", "duration": 10},
    {"color": "amber", "duration": 3},
    {"color": "green", "duration": 10},
    {"color": "amber", "duration": 3},
]

# -----------------------------------------------------------------------------
# Metrics Collector
# -----------------------------------------------------------------------------
class BenchmarkMetrics:
    def __init__(self):
        self.lock = threading.Lock()
        self.start_time = time.time()
        self.total_requests = 0
        self.success_requests = 0
        self.failed_requests = 0
        self.latencies_ms = []
        self.status_codes = {}
        self.errors = []

    def record_request(self, status_code: int, latency_ms: float, error_msg: str = None):
        with self.lock:
            self.total_requests += 1
            if 200 <= status_code < 300:
                self.success_requests += 1
            else:
                self.failed_requests += 1

            self.latencies_ms.append(latency_ms)
            self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
            if error_msg:
                self.errors.append(error_msg)

    def print_summary(self):
        with self.lock:
            elapsed = time.time() - self.start_time
            if not self.latencies_ms:
                print("\n[Metrics] No requests were recorded.")
                return

            sorted_latencies = sorted(self.latencies_ms)
            count = len(sorted_latencies)
            p50 = sorted_latencies[int(count * 0.50)]
            p90 = sorted_latencies[int(count * 0.90)]
            p95 = sorted_latencies[int(count * 0.95)]
            p99 = sorted_latencies[int(count * 0.99)]
            avg_lat = sum(sorted_latencies) / count
            min_lat = sorted_latencies[0]
            max_lat = sorted_latencies[-1]
            rps = self.total_requests / elapsed if elapsed > 0 else 0

            print("\n" + "=" * 60)
            print("                 BENCHMARK SUMMARY")
            print("=" * 60)
            print(f"Elapsed Time       : {elapsed:.2f} s")
            print(f"Total Requests     : {self.total_requests}")
            print(f"Successful (2xx)   : {self.success_requests} ({(self.success_requests / self.total_requests)*100:.1f}%)")
            print(f"Failed (non-2xx)   : {self.failed_requests} ({(self.failed_requests / self.total_requests)*100:.1f}%)")
            print(f"Throughput         : {rps:.2f} req/s")
            print("-" * 60)
            print(f"Latency Min        : {min_lat:.2f} ms")
            print(f"Latency Avg        : {avg_lat:.2f} ms")
            print(f"Latency Median(p50): {p50:.2f} ms")
            print(f"Latency p90        : {p90:.2f} ms")
            print(f"Latency p95        : {p95:.2f} ms")
            print(f"Latency p99        : {p99:.2f} ms")
            print(f"Latency Max        : {max_lat:.2f} ms")
            print("-" * 60)
            print(f"Status Codes       : {self.status_codes}")
            if self.errors:
                print(f"Sample Errors ({min(5, len(self.errors))} of {len(self.errors)}):")
                for err in self.errors[:5]:
                    print(f"  - {err}")
            print("=" * 60 + "\n")


# -----------------------------------------------------------------------------
# Traffic Light Worker
# -----------------------------------------------------------------------------
def traffic_light_worker(
    camera_id: str,
    location: list,
    base_url: str,
    jwt_token: str,
    enable_heartbeat: bool,
    metrics: BenchmarkMetrics,
    stop_event: threading.Event,
    max_start_delay: float = 26.0,
):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {jwt_token}",
        "User-Agent": camera_id,
    }

    event_url = f"{base_url}/cameras/{camera_id}/ingest"
    heartbeat_url = f"{base_url}/cameras/{camera_id}/heartbeat"

    short_id = camera_id[:8]
    start_delay = random.uniform(0.0, max_start_delay)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [{short_id}] Scheduled to start in {start_delay:.2f}s (randomized start)")

    # Wait for the randomized start time
    if stop_event.wait(start_delay):
        return

    last_event_ts = int(time.time() * 1000)

    # Optional background heartbeat thread for this camera
    def heartbeat_loop():
        nonlocal last_event_ts
        with httpx.Client(headers=headers, timeout=10.0, follow_redirects=True) as hb_client:
            while not stop_event.is_set():
                # Send heartbeat every 5 seconds
                if stop_event.wait(5):
                    break

                hb_payload = {
                    "state": "online",
                    "location": location,
                    "last_event_timestamp": last_event_ts,
                    "battery_level": 92.0,
                    "firmware_version": "1.0.4",
                    "wifi_signal": -62,
                }
                start_t = time.perf_counter()
                try:
                    resp = hb_client.post(heartbeat_url, json=hb_payload)
                    lat = (time.perf_counter() - start_t) * 1000
                    metrics.record_request(resp.status_code, lat)
                except Exception as e:
                    lat = (time.perf_counter() - start_t) * 1000
                    metrics.record_request(0, lat, error_msg=f"Heartbeat [{camera_id[:8]}]: {e}")

    if enable_heartbeat:
        hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        hb_thread.start()

    with httpx.Client(headers=headers, timeout=10.0, follow_redirects=True) as client:
        step_idx = 0

        while not stop_event.is_set():
            current_step = LIGHT_CYCLE[step_idx % len(LIGHT_CYCLE)]
            color = current_step["color"]
            duration = current_step["duration"]

            now_ms = int(time.time() * 1000)
            last_event_ts = now_ms

            payload = {
                "events": [
                    {
                        "type": "light_change",
                        "color": color,
                        "timestamp": now_ms,
                    }
                ]
            }

            start_t = time.perf_counter()
            status_code = 0
            err_msg = None
            try:
                resp = client.post(event_url, json=payload)
                lat = (time.perf_counter() - start_t) * 1000
                status_code = resp.status_code
                if status_code != 200:
                    err_msg = f"HTTP {status_code}: {resp.text[:100]}"
                metrics.record_request(status_code, lat, err_msg)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [{short_id}] Light -> {color.upper():<5} | Status: {status_code} | Latency: {lat:.1f}ms | Next in {duration}s")
            except Exception as e:
                lat = (time.perf_counter() - start_t) * 1000
                err_msg = str(e)
                metrics.record_request(0, lat, err_msg=f"Event [{short_id}]: {e}")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [{short_id}] Light -> {color.upper():<5} | ERROR: {e} ({lat:.1f}ms)")

            # Wait duration before the next color transition
            if stop_event.wait(duration):
                break

            step_idx += 1


# -----------------------------------------------------------------------------
# Main Runner
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Traffic Light API Benchmark & Simulator")
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help=f"API Base URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--token", default=os.getenv("JWT_TOKEN", CAMERA_JWT), help="JWT Bearer Token")
    parser.add_argument("--no-heartbeat", action="store_true", help="Disable background 5s heartbeat requests")
    parser.add_argument("--duration", type=int, default=0, help="Run duration in seconds (0 = run indefinitely until Ctrl+C)")
    parser.add_argument("--max-delay", type=float, default=26.0, help="Maximum random startup delay in seconds (default: 26.0)")
    args = parser.parse_args()

    jwt_token = args.token.strip()
    if not jwt_token:
        print("[Error] No JWT Token provided.")
        print("Please provide it via --token <JWT>, set the JWT_TOKEN environment variable, or edit DEFAULT_JWT_TOKEN in benchmark.py.")
        sys.exit(1)

    print("=" * 60)
    print("        TRAFFIC LIGHT API BENCHMARK / SIMULATOR")
    print("=" * 60)
    print(f"Target URL         : {args.url}")
    print(f"Traffic Lights     : {len(TRAFFIC_LIGHTS)} cameras")
    print(f"Cycle Sequence     : Red (10s) -> Amber/Yellow (3s) -> Green (10s) -> Amber/Yellow (3s)")
    print(f"Heartbeat Enabled  : {not args.no_heartbeat} (every 5 seconds)")
    print(f"Random Start Delay : 0.0s to {args.max_delay:.1f}s")
    if args.duration > 0:
        print(f"Run Duration       : {args.duration} seconds")
    else:
        print("Run Duration       : Indefinite (Press Ctrl+C to stop and view metrics)")
    print("=" * 60)

    metrics = BenchmarkMetrics()
    stop_event = threading.Event()
    threads = []

    for item in TRAFFIC_LIGHTS:
        t = threading.Thread(
            target=traffic_light_worker,
            args=(
                item["uuid"],
                item["location"],
                args.url,
                jwt_token,
                not args.no_heartbeat,
                metrics,
                stop_event,
                args.max_delay,
            ),
            daemon=True,
        )
        threads.append(t)
        t.start()

    print(f"\n[+] Started {len(threads)} traffic light threads. Mimicking lights...\n")

    try:
        start_time = time.time()
        while True:
            if args.duration > 0 and (time.time() - start_time) >= args.duration:
                print(f"\n[!] Target duration of {args.duration}s reached.")
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n\n[!] Stopping benchmark (Ctrl+C pressed)...")
    finally:
        stop_event.set()
        # Allow threads a moment to cleanly exit
        time.sleep(1)
        metrics.print_summary()

if __name__ == "__main__":
    main()
