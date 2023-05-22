"""Listeners related module."""
import asyncio
from typing import List
from typing import Optional

from bosch.control_panel.cc880p.models.constants import Id
from bosch.control_panel.cc880p.models.cp import Area
from bosch.control_panel.cc880p.models.cp import Availability
from bosch.control_panel.cc880p.models.cp import ControlPanel
from bosch.control_panel.cc880p.models.cp import ControlPanelEntity
from bosch.control_panel.cc880p.models.cp import Output
from bosch.control_panel.cc880p.models.cp import Siren
from bosch.control_panel.cc880p.models.cp import Time
from bosch.control_panel.cc880p.models.cp import Zone


class BaseControlPanelListener:
    """Base class for implementation of event listeners."""

    async def on_availability_changed(self, entity: Availability):
        """On availability changed."""

    async def on_area_changed(self, entity: Area):
        """On area changed."""

    async def on_siren_changed(self, entity: Siren):
        """On siren changed."""

    async def on_zone_trigger_changed(self, id: Id, entity: Zone):
        """On zone trigger changed."""

    async def on_zone_enabling_changed(self, id: Id, entity: Zone):
        """On zone enabling changed."""

    async def on_zone_changed(self, id: Id, entity: Zone):
        """On zone changed."""

    async def on_output_changed(self, id: Id, entity: Output):
        """On output changed."""

    async def on_time_changed(self, entity: Time):
        """On time changed."""

    async def on_changed(
        self, entity: ControlPanelEntity, id: Optional[Id] = None
    ):
        """On anything changed on the control panel."""

    async def on_data(self, data: bytes):
        """On data changed."""


class EventProducer:
    """Event producer."""

    def __init__(self, cp: ControlPanel):
        """Initialize the event producer."""
        self._listeners: List[BaseControlPanelListener] = []
        self.cp = cp

    def add_listener(self, listener: BaseControlPanelListener):
        """Add a single listener."""
        if isinstance(listener, BaseControlPanelListener):
            self._listeners.append(listener)
        else:
            raise ValueError(
                'Listener must inherit from BaseListener or implement the '
                'interface.'
            )

    def remove_listener(self, listener: BaseControlPanelListener):
        """Remove a single listener."""
        self._listeners.remove(listener)

    def clear_listeners(self):
        """Remove all listeners."""
        self._listeners.clear()

    async def _notify(self, name: str, *args, **kwargs):
        await asyncio.gather(*[
            getattr(
                listener,
                f'on_{name}'
            )(*args, **kwargs) for listener in self._listeners
        ])

    async def notify_availability_changed(self):
        """Notify availability change."""
        await self._notify('availability_changed', self.cp.availability)
        await self.notify_changed(self.cp.availability)

    async def notify_area_changed(self):
        """Notify area change."""
        await self._notify('area_changed', self.cp.areas[1])
        await self.notify_changed(self.cp.areas[1], 1)

    async def notify_siren_changed(self):
        """Notify siren change."""
        await self._notify('siren_changed', self.cp.siren)
        await self.notify_changed(self.cp.siren)

    async def notify_zone_trigger_changed(self, id: Id):
        """Notify a zone trigger change."""
        await self._notify('zone_trigger_changed', id, self.cp.zones[id])
        await self.notify_zone_changed(id)

    async def notify_zone_enabling_changed(self, id: Id):
        """Notify a zone enabled change."""
        await self._notify('zone_enabling_changed', id, self.cp.zones[id])
        await self.notify_zone_changed(id)

    async def notify_zone_changed(self, id: Id):
        """Notify a zone change."""
        await self._notify('zone_changed', id, self.cp.zones[id])
        await self.notify_changed(self.cp.zones[id], id)

    async def notify_output_changed(self, id: Id):
        """Notify a output change."""
        await self._notify('output_changed', id, self.cp.outputs[id])
        await self.notify_changed(self.cp.outputs[id], id)

    async def notify_time_changed(self):
        """Notify time change."""
        await self._notify('time_changed', self.cp.time)
        await self.notify_changed(self.cp.time)

    async def notify_changed(
        self, entity: ControlPanelEntity, id: Optional[Id] = None
    ):
        """Notify anything changed on the control panel."""
        await self._notify('changed', entity, id)

    async def notify_data(self, data: bytes):
        """Notify data."""
        await self._notify('data', data)
