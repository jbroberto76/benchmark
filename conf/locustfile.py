import time
from locust import FastHttpUser, task, between
import locust.stats
locust.stats.PERCENTILES_TO_REPORT = [0.5, 0.95, 0.99]

class QuickstartUser(FastHttpUser):
    wait_time = between(3, 10)

    @task
    def bitex(self):
        self.client.client.clientpool.close()
        self.client.get("/")
        self.client.get("/list/smartphones")
        self.client.get("/list/tvs")
        self.client.get("/list/video-games")
        self.client.get("/list/tablets")
        self.client.get("/list/watches")
        # self.client.get("/product/6a0e03f653c25a7921107e60")
        # self.client.get("/product/6a0e10b52a2b8afd79abee64")
        # self.client.get("/product/6a0e10f42a2b8afd79abee65")
        # self.client.get("/product/6a0e0ffb2a2b8afd79abee62")
        # self.client.get("/product/6a0e0e7c2a2b8afd79abee5d")
        # self.client.get("/product/6a0e0e3f2a2b8afd79abee5c")

        


    # @task(3)
    # def view_items(self):
    #     for item_id in range(10):
    #         self.client.get(f"/item?id={item_id}", name="/item")
    #         time.sleep(1)

    # def on_start(self):
    #     self.client.post("/login", json={"username":"foo", "password":"bar"})


    #    https://react-demo-omega-orcin.vercel.app/