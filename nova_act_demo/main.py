from nova_act import NovaAct


def main():
    with NovaAct(starting_page="https://nova.amazon.com/act") as nova:
        nova.act(
            "Click the Learn More button."
            "Then, return the title and publication date of the blog."
        )


if __name__ == "__main__":
    main()
