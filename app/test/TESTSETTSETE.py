from abc import ABC, abstractmethod


class IControl(ABC):

    @abstractmethod
    def draw(self):
        pass


class IButton(IControl):

    @abstractmethod
    def on_click(self, func):
        pass

    @abstractmethod
    def click(self):
        pass


class Menu(IControl):
    def draw(self):
        print("Drawing menu...")


class Button(IButton):

    def __init__(self):
        self.callback = None

    def draw(self):
        print("Drawing button...")

    def click(self):
        if self.callback:
            self.callback("Button was clicked!")

    def on_click(self, func):
        self.callback = func


class Checkbox(Button):
    def __init__(self):
        super().__init__()
        self.checked = False

    def draw(self):
        super().draw()
        print("Drawing checkbox...")

    def click(self):
        self.checked = not self.checked
        super().click()


class Applicaton:

    def __init__(self):
        self.controls: list[IControl] = []

    def go(self):  #Business logic

        for control in self.controls:

            if isinstance(control, IButton):
                control.on_click(
                    lambda x: print(x)
                )

            control.draw()

        print('Drawn')

    def add_control(self, in_control: IControl):
        self.controls.append(in_control)


def main():
    app = Applicaton()

    special_button = Button()

    app.add_control(Menu())
    app.add_control(special_button)
    app.add_control(Checkbox())


    app.go()


    special_button.click()


if __name__ == "__main__":
    main()
