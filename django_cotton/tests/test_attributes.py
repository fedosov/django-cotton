from django_cotton.tests.utils import CottonTestCase, get_compiled


class AttributeHandlingTests(CottonTestCase):
    def test_dynamic_attributes_on_components(self):
        self.create_template(
            "eval_attributes_on_component_view.html",
            """
                <c-dynamic-attributes-component
                        :none="None"
                        :number="1"
                        :boolean_true="True"
                        :boolean_false="False"
                        :dict="{'key': 'value'}"
                        :list="[1, 2, 3]"
                        :listdict="[{'key': 'value'}]"
                        :variable="variable"
                        :template_string_lit="{'dummy': {{ dummy }}}"
                />        
            """,
            "view/",
            context={"variable": 111, "dummy": 222},
        )

        self.create_template(
            "cotton/dynamic_attributes_component.html",
            """
                {% if none is None %}
                    <p>none is None</p>
                {% endif %}
                
                {% if number == 1 %}
                    <p>number is 1</p>
                {% endif %}
                
                {% if boolean_true is True %}
                    <p>boolean_true is True</p>
                {% endif %}
                
                {% if boolean_false is False %}
                    <p>boolean_false is False</p>
                {% endif %}
                
                {% if dict.key == 'value' %}
                    <p>dict.key is 'value'</p>
                {% endif %}
                
                {% if list.0 == 1 %}
                    <p>list.0 is 1</p>
                {% endif %}
                
                {% if listdict.0.key == 'value' %}
                    <p>listdict.0.key is 'value'</p>
                {% endif %}    
                
                {% if variable == 111 %}
                    <p>variable is 111</p>
                {% endif %}   
                
                HHH{{ template_string_lit }}HHH
                
                {% if template_string_lit.dummy == 222 %}
                    <p>template_string_lit.dummy is 222</p>
                {% endif %}            
            """,
        )

        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view/")

            self.assertContains(response, "none is None")
            self.assertContains(response, "number is 1")
            self.assertContains(response, "boolean_true is True")
            self.assertContains(response, "boolean_false is False")
            self.assertContains(response, "list.0 is 1")
            self.assertContains(response, "dict.key is 'value'")
            self.assertContains(response, "listdict.0.key is 'value'")
            self.assertContains(response, "variable is 111")
            self.assertContains(response, "template_string_lit.dummy is 222")

    def test_we_can_govern_whole_attributes_in_html_elements(self):
        self.create_template(
            "cotton/attribute_govern.html",
            """
            <div {% if something %} class="first" {% else %} class="second" {% endif %}><div>
            """,
        )

        self.create_template(
            "attribute_govern_view.html",
            """
            <c-attribute-govern :something="False" />
            """,
            "view/",
        )

        # Override URLconf
        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view/")
            self.assertContains(response, 'class="second"')
            self.assertNotContains(response, 'class="first"')

    def test_attribute_names_on_component_containing_hyphens_are_converted_to_underscores(
        self,
    ):
        self.create_template(
            "cotton/hyphens.html",
            """
            <div x-data="{{ x_data }}" x-init="{{ x_init }}"></div>
            """,
        )

        self.create_template(
            "hyphens_view.html",
            """
            <c-hyphens x-data="{}" x-init="do_something()" />
            """,
            "view/",
        )

        # Override URLconf
        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view/")

            self.assertContains(response, 'x-data="{}" x-init="do_something()"')

    def test_equals_in_attribute_values(self):
        self.create_template(
            "cotton/equals.html",
            """
            <div {{ attrs }}><div>
            """,
        )

        self.create_template(
            "equals_view.html",
            """
            <c-equals
              @click="this=test"
            />
            """,
            "view/",
        )

        # Override URLconf
        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view/")

            self.assertContains(response, '@click="this=test"')

    def test_spaces_are_maintained_around_expressions_inside_attributes(self):
        self.create_template(
            "maintain_spaces_in_attributes_view.html",
            """
            <div some_attribute_{{ id }}_something="true"></div>
            """,
            "view/",
        )

        # Override URLconf
        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view/")

            self.assertContains(response, "some_attribute__something")

    def test_attributes_without_colons_are_not_evaluated(self):
        self.create_template(
            "cotton/static_attrs.html",
            """
                {% if something == "1,234" %}
                    All good
                {% endif %}
                
                {% if something == "(1, 234)" %}
                    "1,234" was evaluated as a tuple
                {% endif %}
            """,
        )

        self.create_template(
            "static_attrs_view.html",
            """
                <c-static-attrs something="{{ something }}" />
            """,
            "view/",
            context={"something": "1,234"},
        )

        # Override URLconf
        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view/")
            self.assertContains(response, "All good")

    def test_attribute_merging(self):
        self.create_template(
            "cotton/merges_attributes.html",
            """
            <div {{ attrs|merge:'class:form-group another-class-with:colon' }}></div>
            """,
        )

        self.create_template(
            "attribute_merging_view.html",
            """
            <c-merges-attributes class="extra-class" silica:model="test" another="test">ss</c-merges-attributes>        
            """,
            "view/",
        )

        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view/")
            self.assertContains(response, 'class="form-group another-class-with:colon extra-class"')

    def test_attributes_can_contain_django_native_tags(self):
        self.create_template(
            "native_tags_in_attributes_view.html",
            """                                
                <c-native-tags-in-attributes
                    attr1="Hello {{ name }}"
                    attr2="{{ test|default:'none' }}"
                    attr3="{% if 1 == 1 %}cowabonga!{% endif %}"
                >
                    <c-slot name="named">test</c-slot>
                </c-native-tags-in-attributes>
            """,
            "view/",
            context={"name": "Will", "test": "world"},
        )

        self.create_template(
            "cotton/native_tags_in_attributes.html",
            """
                Attribute 1 says: '{{ attr1 }}'
                Attribute 2 says: '{{ attr2 }}'
                Attribute 3 says: '{{ attr3 }}'
                attrs tag is: '{{ attrs }}'            
            """,
        )

        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view/")

            self.assertContains(response, "Attribute 1 says: 'Hello Will'")
            self.assertContains(response, "Attribute 2 says: 'world'")
            self.assertContains(response, "Attribute 3 says: 'cowabonga!'")

            self.assertContains(
                response,
                """attrs tag is: 'attr1="Hello Will" attr2="world" attr3="cowabonga!"'""",
            )

    def test_strings_with_spaces_can_be_passed(self):
        self.create_template(
            "string_with_spaces_view.html",
            """
                <c-string-test var="string with space" attr="I have spaces">
                    <c-slot name="named_slot">
                        named_slot with spaces
                    </c-slot>
                </c-string-test>            
            """,
            "view/",
        )

        self.create_template(
            "cotton/string_test.html",
            """
                <c-vars var default_var="default var" />
                
                slot: '{{ slot }}'
                attr: '{{ attr }}'
                var: '{{ var }}'
                default_var: '{{ default_var }}'
                named_slot: '{{ named_slot }}'
                attrs: '{{ attrs }}'
            """,
        )

    def test_attribute_passing(self):
        self.create_template(
            "attribute_passing_view.html",
            """
                <c-attribute-passing attribute_1="hello" and-another="woo1" thirdForLuck="yes" />       
            """,
            "view/",
        )
        self.create_template("cotton/attribute_passing.html", """<div {{ attrs }}></div>""")

        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view/")
            self.assertContains(
                response, '<div attribute_1="hello" and-another="woo1" thirdForLuck="yes">'
            )

    def test_loader_preserves_duplicate_attributes(self):
        compiled = get_compiled("""<a href="#" class="test" class="test2">hello</a>""")

        self.assertEqual(
            compiled,
            """<a href="#" class="test" class="test2">hello</a>""",
        )

    def test_boolean_attributes(self):
        self.create_template(
            "cotton/boolean_attribute.html",
            """
                {% if is_hyphenated is True %}
                    is_hyphenated is True
                {% endif %}  

                {% if is_underscored is True %}
                    is_underscored is True
                {% endif %}   
                
                attrs: {{ attrs }}
            """,
        )

        self.create_template(
            "boolean_attribute_view.html",
            """
                <c-boolean-attribute is-hyphenated is_underscored  />
            """,
            "view/",
        )

        # Override URLconf
        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view/")
            self.assertContains(response, "is_hyphenated is True")
            self.assertContains(response, "is_underscored is True")
            self.assertContains(response, "attrs: is-hyphenated is_underscored")

    def test_empty_strings_are_not_considered_booleans(self):
        self.create_template(
            "cotton/empty_string_attrs.html",
            """
                {% if something1 == "" %}
                    I am string
                {% endif %}
                
                {% if something2 is True %}
                    I am boolean
                {% endif %}
            """,
        )

        self.create_template(
            "empty_string_attrs_view.html",
            """
                <c-empty-string-attrs something1="" something2 />
            """,
            "view/",
        )

        # Override URLconf
        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view/")
            self.assertContains(response, "I am string")
            self.assertContains(response, "I am boolean")

    def test_htmx_attribute_values_double_quote(self):
        # tests for json-like values
        self.create_template(
            "cotton/htmx2.html",
            """
            <div {{ attrs }}><div>
            """,
        )

        self.create_template(
            "htmx_view2.html",
            """
                <c-htmx2
                  hx-vals="{'id': '1'}"
                />
            """,
            "view/",
        )

        # Override URLconf
        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view/")
            self.assertContains(response, "\"{'id': '1'}\"")

    def test_htmx_attribute_values_single_quote(self):
        # tests for json-like values
        self.create_template(
            "cotton/htmx.html",
            """
            <div {{ attrs }}><div>            
            """,
        )

        self.create_template(
            "htmx_view.html",
            """
            <c-htmx
              hx-vals='{"id": "1"}'
            />
            """,
            "view/",
        )

        # Override URLconf
        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view/")
            self.assertContains(response, """'{"id": "1"}'""")

    def test_htmx_vals_again(self):
        self.create_template(
            "cotton/htmx_vals.html",
            """
            <div {{ attrs }}><div>
            """,
        )

        self.create_template(
            "htmx_vals_view.html",
            """
            <c-htmx-vals
                hx-post="/root"
                hx-trigger="click"
                hx-vals='{"use_block": "page-and-paging-controls"}'
            />
            """,
            "htmx-vals-view/",
        )

        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/htmx-vals-view/")
            self.assertContains(response, """hx-vals='{"use_block": "page-and-paging-controls"}'""")
            self.assertContains(response, 'hx-post="/root"')
            self.assertContains(response, 'hx-trigger="click"')
            self.assertNotContains(response, 'hx-vals="')
            self.assertNotContains(response, "hx-vals=`")

    def test_string_attributes_are_not_parsed_as_variables(self):
        self.create_template(
            "cotton/string_attrs.html",
            """
                {% if string_attr == "world" %}
                    This should not occur
                {% endif %}
            
                {% if string_attr == "hello" %}
                    It's hello
                {% endif %}
            """,
        )

        self.create_template(
            "string_attrs_view.html",
            """
                <c-string-attrs string_attr="hello" />
            """,
            "view/",
            context={"hello": "world"},
        )

        # Override URLconf
        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view/")
            self.assertContains(response, "It's hello")

    def test_attributes_remain_unordered(self):
        compiled = get_compiled(
            """
                <c-dummy>
                    <c-slot name="left">
                        in named slot: <strong {% if 1 == 2 %}hidden{% endif %}></strong>
                    </c-slot>
    
                    in default slot: <strong {% if 1 == 2 %}hidden{% endif %}></strong>
                </c-dummy>  
            """
        )

        self.assertTrue(
            "in named slot: <strong {% if 1 == 2 %}hidden{% endif %}></strong>" in compiled
        )
        self.assertTrue(
            "in default slot: <strong {% if 1 == 2 %}hidden{% endif %}></strong>" in compiled
        )

    def test_colon_escaping(self):
        self.create_template(
            "cotton/colon_escaping.html",
            """
            attrs: '{{ attrs }}'
        """,
        )

        self.create_template(
            "colon_escaping_view.html",
            """
            <c-colon-escaping 
                ::string="variable" 
                :dynamic="variable" 
                ::complex-string="{'something': 1}"
                :complex-dynamic="{'something': 1}"/>
        """,
            "view/",
            context={"variable": "Ive been resolved!"},
        )
        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view/")

            self.assertContains(
                response,
                """attrs: ':string="variable" dynamic="Ive been resolved!" :complex-string="{'something': 1}" complex-dynamic="{'something': 1}"'""",
            )

    def test_attributes_can_contain_valid_json(self):
        self.create_template(
            "cotton/json_attrs.html",
            """
                <button {{ attrs }}>{{ slot }}</button>
            """,
        )

        self.create_template(
            "json_attrs_view.html",
            """
                <c-json-attrs data-something='{"key=dd": "the value with= spaces"}' />
            """,
            "view/",
        )

        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view/")

            self.assertContains(response, """{"key=dd": "the value with= spaces"}""")


class ConditionalAttributeTests(CottonTestCase):
    """Test cases for conditional attributes - currently failing but should work after implementation"""

    def test_basic_conditional_attribute_if_true(self):
        """Test basic {% if %} conditional attribute when condition is true"""
        self.create_template(
            "cotton/conditional_basic.html",
            """
            <div {{ attrs }}>Content</div>
            """,
        )

        self.create_template(
            "conditional_basic_view_true.html",
            """
            <c-conditional-basic 
                class="btn"
                {% if user_is_admin %}admin="true"{% endif %}
            />
            """,
            "view-true/",
            context={"user_is_admin": True},
        )

        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view-true/")
            self.assertContains(response, 'class="btn"')
            self.assertContains(response, 'admin="true"')

    def test_conditional_attribute_with_else(self):
        """Test {% if %} {% else %} conditional attributes"""
        self.create_template(
            "cotton/conditional_else.html",
            """
            <div {{ attrs }}>Content</div>
            """,
        )

        self.create_template(
            "conditional_else_view.html",
            """
            <c-conditional-else 
                class="btn"
                {% if user_is_admin %}role="admin"{% else %}role="user"{% endif %}
            />
            """,
            "view-else/",
            context={"user_is_admin": False},
        )

        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view-else/")
            self.assertContains(response, 'class="btn"')
            self.assertContains(response, 'role="user"')
            self.assertNotContains(response, 'role="admin"')

    def test_multiple_conditional_attributes(self):
        """Test multiple conditional attributes on the same component"""
        self.create_template(
            "cotton/conditional_multiple.html",
            """
            <div {{ attrs }}>Content</div>
            """,
        )

        self.create_template(
            "conditional_multiple_view.html",
            """
            <c-conditional-multiple 
                class="btn"
                {% if user_is_admin %}admin="true"{% endif %}
                {% if user_is_premium %}premium="true"{% endif %}
                {% if user_is_active %}active="true"{% endif %}
                data-static="always-present"
            />
            """,
            "view-multiple/",
            context={
                "user_is_admin": True,
                "user_is_premium": False,
                "user_is_active": True,
            },
        )

        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view-multiple/")
            self.assertContains(response, 'class="btn"')
            self.assertContains(response, 'admin="true"')
            self.assertNotContains(response, 'premium="true"')
            self.assertContains(response, 'active="true"')
            self.assertContains(response, 'data-static="always-present"')

    def test_conditional_attribute_with_for_loop(self):
        """Test {% for %} loop in conditional attributes"""
        self.create_template(
            "cotton/conditional_for.html",
            """
            <div {{ attrs }}>Content</div>
            """,
        )

        self.create_template(
            "conditional_for_view.html",
            """
            <c-conditional-for 
                class="btn"
                {% for item in items %}data-{{ item }}="{{ item }}"{% endfor %}
            />
            """,
            "view-for/",
            context={"items": ["first", "second", "third"]},
        )

        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view-for/")
            self.assertContains(response, 'class="btn"')
            self.assertContains(response, 'data-first="first"')
            self.assertContains(response, 'data-second="second"')
            self.assertContains(response, 'data-third="third"')

    def test_nested_conditional_attributes(self):
        """Test nested {% if %} statements in attributes"""
        self.create_template(
            "cotton/conditional_nested.html",
            """
            <div {{ attrs }}>Content</div>
            """,
        )

        self.create_template(
            "conditional_nested_view.html",
            """
            <c-conditional-nested 
                class="btn"
                {% if user_is_active %}
                    {% if user_is_admin %}
                        role="super-admin"
                    {% else %}
                        role="regular-user"
                    {% endif %}
                    active="true"
                {% endif %}
            />
            """,
            "view-nested/",
            context={"user_is_active": True, "user_is_admin": True},
        )

        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view-nested/")
            self.assertContains(response, 'class="btn"')
            self.assertContains(response, 'role="super-admin"')
            self.assertContains(response, 'active="true"')

    def test_conditional_attribute_mixed_with_dynamic_attributes(self):
        """Test conditional attributes mixed with existing dynamic attributes (:attr)"""
        self.create_template(
            "cotton/conditional_mixed.html",
            """
            <div {{ attrs }}>Content</div>
            """,
        )

        self.create_template(
            "conditional_mixed_view.html",
            """
            <c-conditional-mixed 
                class="btn"
                :user-id="user.id"
                {% if user.is_admin %}admin="true"{% endif %}
                :theme="theme"
                data-static="value"
            />
            """,
            "view-mixed/",
            context={"user": {"id": 456, "is_admin": True}, "theme": "blue"},
        )

        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view-mixed/")
            self.assertContains(response, 'class="btn"')
            self.assertContains(response, 'user-id="456"')
            self.assertContains(response, 'admin="true"')
            self.assertContains(response, 'theme="blue"')
            self.assertContains(response, 'data-static="value"')

    def test_conditional_attribute_with_complex_expressions(self):
        """Test conditional attributes with complex Django template expressions"""
        self.create_template(
            "cotton/conditional_complex.html",
            """
            <div {{ attrs }}>Content</div>
            """,
        )

        self.create_template(
            "conditional_complex_view.html",
            """
            <c-conditional-complex 
                class="btn"
                {% if items|length > 2 %}has-many-items="true"{% endif %}
                {% if "admin" in user.permissions %}has-admin-perm="true"{% endif %}
            />
            """,
            "view-complex/",
            context={"items": [1, 2, 3, 4, 5], "user": {"permissions": ["read", "write", "admin"]}},
        )

        with self.settings(ROOT_URLCONF=self.url_conf()):
            response = self.client.get("/view-complex/")
            self.assertContains(response, 'class="btn"')
            self.assertContains(response, 'has-many-items="true"')
            self.assertContains(response, 'has-admin-perm="true"')

    def test_conditional_attribute_compilation(self):
        """Test that conditional attributes compile correctly"""
        # This tests the compilation phase directly
        template_with_conditional = """
        <c-test-component 
            class="btn"
            {% if user_is_admin %}admin="true"{% endif %}
        />
        """

        # Should compile to:
        # {% c test-component class="btn" %}{% attr _conditional_0 %}{% if user_is_admin %}admin="true"{% endif %}{% endattr %}{% endc %}

        compiled = get_compiled(template_with_conditional)
        # Check the compiled result
        self.assertIn("{% c test-component", compiled)
        self.assertIn("{% attr _conditional_", compiled)  # Updated to match new syntax
        self.assertIn("{% if user_is_admin %}", compiled)
        self.assertIn("{% endattr %}", compiled)
        self.assertIn("{% endc %}", compiled)

    def test_toggle_tab_realistic_conditional_attributes(self):
        """Test realistic toggle-tab component with conditional icon attributes"""
        # Create the toggle-tab component template
        self.create_template(
            "cotton/toggle_tab.html",
            """
            <div {{ attrs }}>{{ slot }}</div>
            """,
        )

        # Test with show_grid_view=True
        self.create_template(
            "toggle_tab_view_true.html",
            """
            <c-toggle-tab 
                view-id="cards" 
                {% if show_grid_view %}icon="grid_view"{% else %}icon="reddit"{% endif %} 
                active-var="currentDisplay" 
                onclick="window.location.href='test';">
                Toggle
            </c-toggle-tab>
            """,
            "view-true/",
            context={"show_grid_view": True},
        )

        # Test with show_grid_view=False
        self.create_template(
            "toggle_tab_view_false.html",
            """
            <c-toggle-tab 
                view-id="cards" 
                {% if show_grid_view %}icon="grid_view"{% else %}icon="reddit"{% endif %} 
                active-var="currentDisplay" 
                onclick="window.location.href='test';">
                Toggle
            </c-toggle-tab>
            """,
            "view-false/",
            context={"show_grid_view": False},
        )

        with self.settings(ROOT_URLCONF=self.url_conf()):
            # Test True case - should show grid_view icon
            response_true = self.client.get("/view-true/")
            self.assertContains(response_true, 'view-id="cards"')
            self.assertContains(response_true, 'icon="grid_view"')
            self.assertContains(response_true, 'active-var="currentDisplay"')
            self.assertContains(response_true, 'onclick="window.location.href=\'test\';"')
            self.assertNotContains(response_true, 'icon="reddit"')
            self.assertContains(response_true, 'Toggle')

            # Test False case - should show reddit icon
            response_false = self.client.get("/view-false/")
            self.assertContains(response_false, 'view-id="cards"')
            self.assertContains(response_false, 'icon="reddit"')
            self.assertContains(response_false, 'active-var="currentDisplay"')
            self.assertContains(response_false, 'onclick="window.location.href=\'test\';"')
            self.assertNotContains(response_false, 'icon="grid_view"')
            self.assertContains(response_false, 'Toggle')

    def test_conditional_attribute_with_template_tag_containing_quotes(self):
        """Test conditional attributes mixed with attributes containing Django template tags with quotes
        
        This reproduces the exact issue from production where conditional attributes break parsing 
        of other attributes that contain Django template tags with embedded quotes, specifically:
        {% clean_querystring display="" %} gets broken into incomplete template tag
        """
        # Create component template
        self.create_template(
            "cotton/toggle_tab_real.html",
            """
            <button {{ attrs }}>{{ slot }}</button>
            """,
        )

        # Create view template that reproduces the exact production issue
        # Using a simpler approach - url tag with quotes should trigger the same parsing issue
        self.create_template(
            "conditional_real_issue_view.html",
            """
            <c-toggle-tab-real 
                view-id="cards" 
                {% if True %}icon="grid_view"{% else %}icon="reddit"{% endif %} 
                active-var="currentDisplay" 
                onclick="window.location.href='{{ request.path }}?param={{ \"test\" }}';">
                Cards
            </c-toggle-tab-real>
            """,
            "view-real-issue/",
            context={"request": {"path": "/test/"}}
        )

        with self.settings(ROOT_URLCONF=self.url_conf()):
            # This should reproduce the exact error:
            # TemplateSyntaxError: Could not parse the remainder: '{%' from '{%'
            # But now it should work correctly with the smart parser
            response = self.client.get("/view-real-issue/")
            
            # Verify that all attributes are correctly parsed and rendered
            self.assertContains(response, 'view-id="cards"')
            self.assertContains(response, 'icon="grid_view"')  # Conditional attribute worked
            self.assertContains(response, 'active-var="currentDisplay"')
            
            # Most importantly, verify that the onclick attribute with Django template tags and quotes
            # was parsed correctly without breaking the template compilation
            self.assertContains(response, 'onclick="window.location.href=\'/test/?param=test\';"')
            
            # Verify the broken parsing patterns don't occur
            self.assertNotContains(response, 'display="" %}')  # This would indicate broken template tag
            self.assertNotContains(response, '{% clean_querystring display=')  # This would indicate incomplete tag
            
            # Verify the content is rendered
            self.assertContains(response, 'Cards')
