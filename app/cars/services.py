class CarService:
    @staticmethod
    def soft_delete(car):
        car.is_active = False
        car.save(update_fields=["is_active"])
