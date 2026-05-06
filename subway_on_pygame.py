import pygame
import random
import sys

# ---------------------------------------------------------
# 1. OOP 아키텍처 및 예외 정의[cite: 1]
# ---------------------------------------------------------

class StationOverloadError(Exception):
    #사용자 정의 예외: 특정 역의 인원이 50명을 넘으면 발생[cite: 1]
    def __init__(self, name, count):
        super().__init__(f"{name}역 과부하: {count}명 대기!")

class Passenger:
    #승객 객체: 목적지 데이터를 가짐[cite: 2]
    def __init__(self, destination_id):
        self.destination_id = destination_id

class Station:
    #지하철역 클래스: 대기열 및 누적 통계 관리[cite: 1, 2]
    def __init__(self, id, name, x, y):
        self.id = id
        self.name = name
        self.x, self.y = x, y
        self.waiting_passengers = []
        self.total_boarded = 0   # 누적 승차[cite: 2]
        self.total_alighted = 0  # 누적 하차[cite: 2]

    def __len__(self):
        #매직 메소드: len(station)으로 대기자 수 확인[cite: 1]
        return len(self.waiting_passengers) 

    def __str__(self):
        #매직 메소드: 역 상태 출력[cite: 1]
        return f"{self.name}역: {len(self)}명 대기 중"

    def add_passengers(self, count, reachable_dests):
        #승객 유입 로직[cite: 2]
        for _ in range(count):
            dest = random.choice(reachable_dests)
            if dest != self.id:
                self.waiting_passengers.append(Passenger(dest))
        
        # 50명 초과 시 예외 발생[cite: 1]
        if len(self) > 50:
            raise StationOverloadError(self.name, len(self))

class BaseTrain:
    #부모 클래스: 열차의 공통 속성 정의[cite: 1]
    def __init__(self, id, color, route_ids):
        self.id = id
        self.color = color
        self.route_ids = route_ids
        self.passengers = [] # AttributeError 방지를 위해 부모에서 생성[cite: 2]

class MetroTrain(BaseTrain):
    #자식 클래스: 실제 운행 및 다형성 탑승 로직 구현[cite: 1, 2]
    CAPACITY = 50

    def __init__(self, id, color, route_ids, start_index, direction):
        # 부모 생성자 호출 (passengers 속성 생성)[cite: 1]
        super().__init__(id, color, route_ids)
        self.current_idx = start_index
        self.direction = direction
        self.target_idx = start_index + direction
        self.progress = 0.0
        self.is_stopped = True
        self.stop_timer = 0

    def update_logic(self, dt, stations_dict):
        #이동 및 정차 로직[cite: 2]
        if self.is_stopped:
            self.stop_timer += dt
            if self.stop_timer > 1500: # 1.5초 정차[cite: 2]
                self.is_stopped = False
                self.stop_timer = 0
                self.set_next_target()
        else:
            self.progress += dt / 2000.0 # 속도[cite: 2]
            if self.progress >= 1.0:
                self.progress = 0.0
                self.current_idx = self.target_idx
                self.is_stopped = True
                self.handle_boarding(stations_dict[self.route_ids[self.current_idx]])

    def set_next_target(self):
        #방향 전환 로직[cite: 2]
        next_val = self.current_idx + self.direction
        if next_val >= len(self.route_ids) or next_val < 0:
            self.direction *= -1
        self.target_idx = self.current_idx + self.direction

    def handle_boarding(self, station):
        #다형성: 역과 열차 간의 데이터 상호작용[cite: 1, 2]
        #하차: 목적지 일치 승객 제거[cite: 2]
        initial_count = len(self.passengers)
        self.passengers = [p for p in self.passengers if p.destination_id != station.id]
        station.total_alighted += (initial_count - len(self.passengers))
        
        # 승차: 해당 노선 포함 승객만 탑승[cite: 2]
        space = self.CAPACITY - len(self.passengers)
        waiting = station.waiting_passengers
        can_board = [p for p in waiting if p.destination_id in self.route_ids]
        cannot_board = [p for p in waiting if p.destination_id not in self.route_ids]
        
        boarding = can_board[:space]
        station.waiting_passengers = can_board[space:] + cannot_board
        self.passengers.extend(boarding)
        station.total_boarded += len(boarding)

# ---------------------------------------------------------
# 2. 시뮬레이션 환경 (Pygame 통합)[cite: 2]
# ---------------------------------------------------------

class SubwaySystem:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((850, 750))
        pygame.display.set_caption("OOP Subway Simulation Demo")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("malgungothic", 12)
        self.bold_font = pygame.font.SysFont("malgungothic", 14, bold=True)
        
        self.alerts = [] # 화면 표시용 경보 리스트[cite: 1]
        self.setup_data()

    def setup_data(self):
        #원본 zip 파일 레이아웃 설정[cite: 2]
        s_data = [
            ('s1', '강남', 100, 300), ('s2', '교대', 200, 300), ('s3', '고속터미널', 300, 200),
            ('s4', '반포', 400, 200), ('s5', '논현', 500, 200), ('s6', '신사', 600, 200),
            ('s7', '남부터미널', 300, 300), ('s8', '양재', 400, 300), ('s9', '매봉', 500, 300),
            ('s10', '도곡', 600, 300), ('s11', '대치', 700, 300),
            ('s12', '압구정', 300, 100), ('s13', '잠원', 400, 100), ('s14', '학여울', 400, 400),
            ('s15', '대청', 400, 500)
        ]
        self.stations = {sid: Station(sid, name, x, y) for sid, name, x, y in s_data}
        self.lines = [['s1', 's2', 's3', 's4', 's5', 's6'], ['s2', 's7', 's8', 's9', 's10', 's11'], ['s12', 's13', 's4', 's8', 's14', 's15']]
        self.line_colors = [(0, 82, 164), (0, 157, 62), (239, 124, 28)]
        
        self.reachable = {}
        for sid in self.stations:
            reach = set()
            for route in self.lines:
                if sid in route: reach.update(route)
            self.reachable[sid] = list(reach)

        self.trains = [
            MetroTrain('T-Blue', self.line_colors[0], self.lines[0], 0, 1),
            MetroTrain('T-Green', self.line_colors[1], self.lines[1], 0, 1),
            MetroTrain('T-Orange', self.line_colors[2], self.lines[2], 0, 1)
        ]

    def add_alert(self, msg):
        #경보 리스트에 추가 및 중복 방지[cite: 1]
        now = pygame.time.get_ticks()
        # 동일한 역의 경보는 최신화만 진행
        station_name = msg.split('역')[0]
        for a in self.alerts:
            if station_name in a['msg']:
                a['msg'] = msg
                a['time'] = now
                return
        self.alerts.insert(0, {'msg': msg, 'time': now})
        if len(self.alerts) > 5: self.alerts.pop()

    def draw_ui(self):
        #통계 및 비상 경보 패널 그리기[cite: 1, 2]
        now = pygame.time.get_ticks()
        
        # 1. 통계 패널
        pygame.draw.rect(self.screen, (255, 255, 255), (600, 40, 230, 100))
        pygame.draw.rect(self.screen, (0, 0, 0), (600, 40, 230, 100), 2)
        total_p = sum(len(s) for s in self.stations.values())
        max_s = max(self.stations.values(), key=lambda s: len(s))
        
        self.screen.blit(self.bold_font.render("System Live Stats", True, (0, 0, 0)), (610, 50))
        self.screen.blit(self.font.render(f"Waiting: {total_p} ppl", True, (50, 50, 50)), (610, 75))
        self.screen.blit(self.font.render(f"Hottest: {max_s.name}({len(max_s)})", True, (200, 0, 0)), (610, 95))

        # 2. 비상 경보 패널 (Emergency Logs)
        bg_alpha = 100 + int(55 * abs(1 - (now % 1000) / 500))
        alert_surf = pygame.Surface((230, 130))
        alert_surf.set_alpha(bg_alpha if self.alerts else 50)
        alert_surf.fill((255, 200, 200))
        self.screen.blit(alert_surf, (600, 160))
        pygame.draw.rect(self.screen, (200, 0, 0), (600, 160, 230, 130), 2)
        self.screen.blit(self.bold_font.render("⚠️ Emergency Logs", True, (150, 0, 0)), (610, 170))
        
        self.alerts = [a for a in self.alerts if now - a['time'] < 5000]
        for i, a in enumerate(self.alerts):
            alpha = max(0, 255 - int(255 * ((now - a['time']) / 5000)))
            txt = self.font.render(f"• {a['msg']}", True, (200, 0, 0))
            txt.set_alpha(alpha)
            self.screen.blit(txt, (610, 195 + (i * 18)))

    def run(self):
        while True:
            dt = self.clock.get_time()
            self.screen.fill((245, 245, 245))
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); sys.exit()

            # 1. 승객 유입 및 예외 처리[cite: 1, 2]
            if random.random() < 0.08:
                sid = random.choice(list(self.stations.keys()))
                try:
                    self.stations[sid].add_passengers(random.randint(1, 4), self.reachable[sid])
                except StationOverloadError as e:
                    self.add_alert(str(e)) # 예외 메시지를 화면 경보로 전달

            # 2. 맵 그리기 (노선)
            for i, route in enumerate(self.lines):
                pts = [(self.stations[s].x, self.stations[s].y) for s in route]
                pygame.draw.lines(self.screen, self.line_colors[i], False, pts, 4)

            # 3. 역 그리기
            for s in self.stations.values():
                radius = 8 + min(len(s) // 4, 12)
                color = (255, 0, 0) if len(s) > 30 else (255, 255, 255)
                pygame.draw.circle(self.screen, color, (s.x, s.y), radius)
                pygame.draw.circle(self.screen, (0, 0, 0), (s.x, s.y), radius, 2)
                self.screen.blit(self.font.render(f"{s.name}({len(s)})", True, (0, 0, 0)), (s.x - 20, s.y + radius + 5))

            # 4. 열차 업데이트 및 그리기
            for t in self.trains:
                t.update_logic(dt, self.stations)
                curr, tgt = self.stations[t.route_ids[t.current_idx]], self.stations[t.route_ids[t.target_idx]]
                tx = curr.x + (tgt.x - curr.x) * t.progress
                ty = curr.y + (tgt.y - curr.y) * t.progress
                pygame.draw.rect(self.screen, t.color, (tx-10, ty-10, 20, 20))
                self.screen.blit(self.font.render(f"{len(t.passengers)}", True, (255, 255, 255)), (tx-6, ty-8))

            self.draw_ui()
            pygame.display.flip()
            self.clock.tick(60)

if __name__ == "__main__":
    SubwaySystem().run()