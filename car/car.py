from abc import ABC, abstractmethod

# Car Interface
class Car(ABC):
    @abstractmethod
    def drive(self) -> None:
        pass

# Concrete Car Classes
class Sedan(Car):
    def drive(self) -> None:
        print("Driving a smooth and comfortable Sedan.")

class SUV(Car):
    def drive(self) -> None:
        print("Driving a rugged and spacious SUV.")

class Hatchback(Car):
    def drive(self) -> None:
        print("Driving a compact and agile Hatchback.")

# CarFactory Abstract Class
class CarFactory(ABC):
    @abstractmethod
    def create_car(self) -> Car:
        pass

# Concrete Factory Classes
class SedanFactory(CarFactory):
    def create_car(self) -> Car:
        return Sedan()

class SUVFactory(CarFactory):
    def create_car(self) -> Car:
        return SUV()

class HatchbackFactory(CarFactory):
    def create_car(self) -> Car:
        return Hatchback()

# Client Code - Demonstration
def manufacture_and_drive(factory: CarFactory) -> None:
    """Client code depends only on abstract CarFactory and Car."""
    car = factory.create_car()
    car.drive()

if __name__ == "__main__":
    # Create factories
    sedan_factory = SedanFactory()
    suv_factory = SUVFactory()
    hatchback_factory = HatchbackFactory()
    
    # Manufacture and drive cars without knowing concrete classes
    print("=== Factory Method Pattern  ===")
    manufacture_and_drive(sedan_factory)
    manufacture_and_drive(suv_factory)
    manufacture_and_drive(hatchback_factory)