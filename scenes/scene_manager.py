"""Scene manager. Use the class directly: SM.register(...), SM.go("name", **kw)."""


class SM:
    scenes = {}
    current = None
    current_name = None

    @classmethod
    def register(cls, name, scene):
        cls.scenes[name] = scene

    @classmethod
    def has(cls, name):
        return name in cls.scenes

    @classmethod
    def go(cls, name, **kw):
        """Switch scenes and call the new scene's on_enter(**kw). False if not registered."""
        scene = cls.scenes.get(name)
        if scene is None:
            return False
        cls.current, cls.current_name = scene, name
        if hasattr(scene, "on_enter"):
            scene.on_enter(**kw)
        return True

    @classmethod
    def update(cls, dt):
        if cls.current:
            cls.current.update(dt)

    @classmethod
    def draw(cls, surf):
        if cls.current:
            cls.current.draw(surf)

    @classmethod
    def handle(cls, ev):
        if cls.current:
            cls.current.handle(ev)
