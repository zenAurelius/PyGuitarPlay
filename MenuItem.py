class MenuItem:
    """A clickable menu item"""

    def __init__(self, name, surf, pos):
        self.surf = surf
        self.pos = pos
        self.name = name
        self.callback = None
        self.is_visible = True

    def draw_on(self, screen):
        if self.is_visible:
            screen.blit(self.surf, self.pos)

    def is_clicked(self, point):
        return (self.is_visible and
                self.surf.get_rect(topleft=self.pos).collidepoint(point))
