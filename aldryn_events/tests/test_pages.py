# -*- coding: utf-8 -*-
import mock

from django.conf import settings
from django.core import mail
from django.core.urlresolvers import reverse

from importlib import import_module
from cms import api
from cms.utils.i18n import force_language
from pyquery import PyQuery

from aldryn_events.models import Event, EventsConfig
from .base import EventBaseTestCase, tz_datetime


class EventPagesTestCase(EventBaseTestCase):

    @mock.patch('aldryn_events.managers.timezone')
    def test_event_detail_page(self, timezone_mock):
        """
        Test if proper url and event page are created
        """
        timezone_mock.now.return_value = tz_datetime(2014, 9, 11, 12)
        event = self.create_default_event()

        # '/events/' came from tests/urls.py, '/open-air/' from the event slug
        self.assertEqual(event.get_absolute_url(), '/en/events/open-air/')
        with force_language('en'):
            response = self.client.get(event.get_absolute_url())
        self.assertContains(response, event.title)

        event.set_current_language('de')
        # '/events/' came from tests/urls.py, '/im-freien/' from the event slug
        self.assertEqual(event.get_absolute_url(), '/de/events/im-freien/')
        with force_language('de'):
            response = self.client.get(event.get_absolute_url())
        self.assertContains(response, event.title)

    @mock.patch('aldryn_events.managers.timezone')
    @mock.patch('aldryn_events.templatetags.aldryn_events.timezone')
    def test_add_event_app_to_page(self, manager_timezone_mock,
                                   tag_timezone_mock):
        """
        When we link event app to any page it should list events
        """
        manager_timezone_mock.now.return_value = tz_datetime(2014, 6, 8)
        tag_timezone_mock.now.return_value = tz_datetime(2014, 6, 8)

        root_page = self.create_root_page(
            publication_date=tz_datetime(2014, 6, 8)
        )
        page = api.create_page(
            title='Events en', template=self.template, language='en',
            slug='eventsapp', published=True,
            parent=root_page,
            apphook='EventListAppHook',
            apphook_namespace=self.app_config.namespace,
            publication_date=tz_datetime(2014, 6, 8)
        )
        api.create_title('de', 'Events de', page, slug='eventsapp')
        page.publish('en')
        page.publish('de')

        # create events
        event1 = Event.objects.language('en').create(
            title='Event2014',
            start_date=tz_datetime(2014, 9, 10),
            publish_at=tz_datetime(2014, 6, 5, 12),
            app_config=self.app_config

        )
        event1.create_translation('de', title='Ereignis', slug='im-freien')
        event2 = Event.objects.language('en').create(
            title='Event2015 only english',
            start_date=tz_datetime(2014, 9, 10),
            publish_at=tz_datetime(2014, 1, 1),
            app_config=self.app_config
        )

        # test english, have 2 events
        with force_language('en'):
            response = self.client.get(page.get_absolute_url('en'))
            self.assertContains(response, event1.title)
            self.assertContains(response, event1.get_absolute_url())
            self.assertContains(response, event2.title)
            self.assertContains(response, event2.get_absolute_url())

        # test german, have 1 event, event 2 is only english
        event1.set_current_language('de')
        with force_language('de'):
            response = self.client.get(page.get_absolute_url('de'))
            self.assertContains(response, event1.title)
            self.assertContains(response, event1.get_absolute_url())
            self.assertNotContains(response, event2.title)
            self.assertNotContains(response, event2.get_absolute_url())

    @mock.patch('aldryn_events.managers.timezone')
    @mock.patch('aldryn_events.templatetags.aldryn_events.timezone')
    def test_unattached_namespace(self, timezone_mock, tag_timezone_mock):
        timezone_mock.now.return_value = tz_datetime(2015, 2, 2, 10)
        tag_timezone_mock.now.return_value = tz_datetime(2015, 2, 2, 10)
        event1 = self.create_event(
            title='Event2015 current namespace',
            slug='open-air',
            start_date=tz_datetime(2015, 2, 7),
            publish_at=tz_datetime(2015, 2, 2, 9)
        )
        event2 = self.create_event(
            title='Event new namespace', slug='open-air-new-namespace',
            start_date=tz_datetime(2015, 2, 7),
            publish_at=tz_datetime(2015, 2, 2, 9),
            app_config=EventsConfig.objects.create(namespace='another')
        )
        response = self.client.get(reverse('aldryn_events:events_list'))
        self.assertContains(response, event1.title)
        self.assertNotContains(response, event2.title)

    @mock.patch('aldryn_events.managers.timezone')
    @mock.patch('aldryn_events.templatetags.aldryn_events.timezone')
    def test_ongoing_events_in_event_list(self, managers_timezone_mock,
                                          tag_timezone_mock):
        managers_timezone_mock.now.return_value = tz_datetime(
            2014, 4, 7, 9, 30
        )
        tag_timezone_mock.now.return_value = tz_datetime(
            2014, 4, 7, 9, 30
        )

        root_page = self.create_root_page(
            publication_date=tz_datetime(2014, 4, 1)
        )
        root_page.publish('en')
        page = api.create_page(
            title='Events en', template=self.template, language='en',
            slug='eventsapp', published=True,
            parent=root_page,
            apphook='EventListAppHook',
            apphook_namespace=self.app_config.namespace,
            publication_date=tz_datetime(2014, 4, 1)
        )
        page.publish('en')

        # happens in Apr 5
        self.create_event(
            title='ev1',
            start_date=tz_datetime(2014, 4, 5),
            publish_at=tz_datetime(2014, 4, 1)
        )
        # Apr 6 12:00 to Apr 7 9:00
        ev2 = self.create_event(
            title='ev2',
            start_date=tz_datetime(2014, 4, 6),
            end_date=tz_datetime(2014, 4, 7),
            start_time='12:00', end_time='09:00',
            publish_at=tz_datetime(2014, 4, 2)
        )
        # happens in Apr 7
        ev3 = self.create_event(
            title='ev3',
            start_date=tz_datetime(2014, 4, 7),
            publish_at=tz_datetime(2014, 4, 3)
        )
        # happens in Apr 8
        self.create_event(
            title='ev4',
            start_date=tz_datetime(2014, 4, 8),
            publish_at=tz_datetime(2014, 4, 4)
        )

        # setUp app config
        original_show_ongoing_first = (
            self.app_config.app_data.config.show_ongoing_first
        )
        self.app_config.app_data.config.show_ongoing_first = True
        self.app_config.save()

        with force_language('en'):
            response = self.client.get(page.get_absolute_url('en'))
            context = response.context_data

        # tearDown app config
        self.app_config.app_data.config.show_ongoing_first = (
            original_show_ongoing_first
        )
        self.app_config.save()

        self.assertQuerysetEqual(
            context['ongoing_objects'], ['ev2', 'ev3'], transform=str
        )
        self.assertQuerysetEqual(
            context['object_list'], ['ev4'], transform=str
        )
        ongoing_list = PyQuery(response.content)('ul.ongoing-events')
        links = ongoing_list.find('h3 a')
        self.assertEqual(2, links.length)
        self.assertEqual(ev2.get_absolute_url(), links[0].attrib['href'])
        self.assertEqual(ev3.get_absolute_url(), links[1].attrib['href'])

    def setUpForEventListPages(self):
        return [
            self.create_event(
                title='ev1',
                start_date=tz_datetime(2014, 3, 7),
                publish_at=tz_datetime(2014, 3, 1),
            ),
            self.create_event(
                title='joint action for development of StarTrek technologies',
                start_date=tz_datetime(2014, 2, 25),
                end_date=tz_datetime(2014, 4, 2),
                publish_at=tz_datetime(2014, 1, 2)
            ),
            self.create_event(
                title='ev3',
                start_date=tz_datetime(2014, 3, 6),
                end_date=tz_datetime(2014, 3, 14),
                publish_at=tz_datetime(2014, 3, 1),
            ),
            self.create_event(
                title='ev4',
                start_date=tz_datetime(2014, 3, 7),
                end_date=tz_datetime(2014, 3, 14),
                publish_at=tz_datetime(2014, 3, 1),
                is_published=False
            ),
            self.create_event(
                # has better way to explain a year event?
                title='womans day is every day',
                start_date=tz_datetime(2013, 3, 8),
                end_date=tz_datetime(2014, 3, 8),
                publish_at=tz_datetime(2013, 3, 8)
            ),
            self.create_event(
                title='ev6',
                start_date=tz_datetime(2014, 3, 23),
                publish_at=tz_datetime(2014, 3, 1)
            ),
            self.create_event(
                title='ev7',
                start_date=tz_datetime(2015, 3, 23),
                publish_at=tz_datetime(2015, 3, 1)
            )
        ]

    def test_event_list_page_by_day(self):
        ev1, ev2, ev3, ev4, ev5, ev6, ev7 = self.setUpForEventListPages()
        url = reverse(
            "aldryn_events:events_list-by-day",
            kwargs={'year': 2014, 'month': 3, 'day': 7}
        )
        with force_language('en'):
            response = self.client.get(url)
            self.assertQuerysetEqual(
                response.context_data['object_list'],
                map(repr, [ev5, ev2, ev3, ev1]),
            )
            self.assertContains(response, ev5.get_absolute_url())
            self.assertContains(response, ev2.get_absolute_url())
            self.assertContains(response, ev3.get_absolute_url())
            self.assertContains(response, ev1.get_absolute_url())

    def test_event_list_page_by_month(self):
        ev1, ev2, ev3, ev4, ev5, ev6, ev7 = self.setUpForEventListPages()
        url = reverse(
            "aldryn_events:events_list-by-month",
            kwargs={'year': 2014, 'month': 3}
        )
        with force_language('en'):
            response = self.client.get(url)
            self.assertQuerysetEqual(
                response.context_data['object_list'],
                map(repr, [ev5, ev2, ev3, ev1, ev6]),
            )
            self.assertContains(response, ev5.get_absolute_url())
            self.assertContains(response, ev2.get_absolute_url())
            self.assertContains(response, ev3.get_absolute_url())
            self.assertContains(response, ev1.get_absolute_url())
            self.assertContains(response, ev6.get_absolute_url())

    def test_event_list_page_by_year(self):
        ev1, ev2, ev3, ev4, ev5, ev6, ev7 = self.setUpForEventListPages()
        url = reverse(
            "aldryn_events:events_list-by-year",
            kwargs={'year': 2014}
        )
        with force_language('en'):
            response = self.client.get(url)
            self.assertQuerysetEqual(
                response.context_data['object_list'],
                map(repr, [ev5, ev2, ev3, ev1, ev6]),
            )
            self.assertContains(response, ev5.get_absolute_url())
            self.assertContains(response, ev2.get_absolute_url())
            self.assertContains(response, ev3.get_absolute_url())
            self.assertContains(response, ev1.get_absolute_url())
            self.assertContains(response, ev6.get_absolute_url())


class RegistrationTestCase(EventBaseTestCase):

    @mock.patch('aldryn_events.models.timezone')
    def test_submit_registration(self, timezone_mock):
        app_config, created = (
            EventsConfig.objects.get_or_create(namespace='aldryn_events')
        )
        app_config = EventsConfig.objects.create(namespace='aldryn_events')
        timezone_mock.now.return_value = tz_datetime(2015, 2, 5, 9)

        with force_language('en'):
            event = Event.objects.create(
                id=5,
                title='Event2014', slug='open-air',
                start_date=tz_datetime(2015, 2, 7),
                publish_at=tz_datetime(2015, 2, 2, 9),
                registration_deadline_at=tz_datetime(2015, 2, 7),
                enable_registration=True,
                app_config=app_config
            )
        event.event_coordinators.create(name='The big boss',
                                        email='theboss@gmail.com')
        event.create_translation('de', title='Ereignis', slug='im-freien')
        event.set_current_language('en')
        data = {
            'salutation': 'mrs',
            'company': 'any',
            'first_name': 'Felipe',
            'last_name': 'Somename',
            'address': 'My Street, 77, Brazil, Earth, Solar system',
            'address_zip': '00000-000',
            'address_city': u'São Paulo',
            'phone': '+55 (11) 1234-5678',
            'mobile': '+55 (11) 1234-5678',
            'email': 'myemail@gmail.com',
            'message': "I'm testing you"
        }
        response = self.client.post(
            event.get_absolute_url(), data
        )

        self.assertRedirects(response, event.get_absolute_url())

        # test if emails was sent
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(
            mail.outbox[0].subject,
            'Thank you for signing up to "{0}"'.format(event.title)
        )
        self.assertEqual(['myemail@gmail.com'], mail.outbox[0].recipients())
        self.assertEqual(
            mail.outbox[1].subject,
            'new registration for "{0}"'.format(event.title)
        )
        self.assertEqual(['theboss@gmail.com'], mail.outbox[1].recipients())

        # test if registration is really on db
        registration = event.registration_set.get()
        for k, v in data.items():
            self.assertEqual(getattr(registration, k), v)

    @mock.patch('aldryn_events.models.timezone')
    def test_reset_registration(self, timezone_mock):
        app_config = EventsConfig.objects.create(namespace='aldryn_events')
        timezone_mock.now.return_value = tz_datetime(2015, 2, 5, 9)

        with force_language('en'):
            event = Event.objects.create(
                title='Event2014', slug='open-air',
                start_date=tz_datetime(2015, 2, 7),
                publish_at=tz_datetime(2015, 2, 2, 9),
                registration_deadline_at=tz_datetime(2015, 2, 7),
                enable_registration=True,
                app_config=app_config
            )
        event.create_translation('de', title='Ereignis2014', slug='im-freien')
        event.event_coordinators.create(name='The big boss',
                                        email='theboss@gmail.com')
        event.registration_set.create(
            salutation='mrs',
            company='any',
            first_name='Felipe',
            last_name='Somename',
            address='My Street, 77, Brazil, Earth, Solar system',
            address_zip='00000-000',
            address_city=u'São Paulo',
            phone='+55 (11) 1234-5678',
            mobile='+55 (11) 1234-5678',
            email='myemail@gmail.com',
            message="I'm testing you"
        )
        with force_language('en'):
            reset_url = reverse(
                'aldryn_events:events_registration_reset',
                kwargs={'slug': event.slug},
                current_app=app_config.namespace
            )
        custom_settings = {
            'SESSION_ENGINE': 'django.contrib.sessions.backends.db'
        }
        with self.settings(**custom_settings):
            # create the session
            engine = import_module(settings.SESSION_ENGINE)
            session = engine.SessionStore()
            session['registered_events'] = [event.pk]
            session.save()

            # Set the cookie to represent the session.
            session_cookie = settings.SESSION_COOKIE_NAME
            self.client.cookies[session_cookie] = session.session_key
            cookie_data = {
                'max-age': None,
                'path': '/',
                'domain': settings.SESSION_COOKIE_DOMAIN,
                'secure': settings.SESSION_COOKIE_SECURE or None,
                'expires': None,
            }
            self.client.cookies[session_cookie].update(cookie_data)

            response = self.client.post(reset_url, {})

        # load session data modified in request
        # Note: need to remove `_session_cache` so updated data is re-loaded
        del session._session_cache
        self.assertEqual(session.get('registered_events'), [])
        self.assertRedirects(response, event.get_absolute_url())